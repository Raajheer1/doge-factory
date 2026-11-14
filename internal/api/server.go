package api

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"doge-factory/internal/analysis"
	"doge-factory/internal/policy"
	"github.com/labstack/echo/v5"
	"github.com/labstack/echo/v5/middleware"
)

type Run struct {
	ID                string             `json:"id"`
	Query             string             `json:"query"`
	Status            string             `json:"status"`
	Stage             string             `json:"stage"`
	Retrieved         int                `json:"retrieved"`
	Reviewed          int                `json:"reviewed"`
	Findings          []analysis.Finding `json:"findings"`
	Errors            []string           `json:"errors"`
	CreatedAt         time.Time          `json:"created_at"`
	SelectedFindingID string             `json:"selected_finding_id,omitempty"`
}
type Server struct {
	repo     policy.Repository
	analyzer analysis.Analyzer
	mu       sync.Mutex
	runs     map[string]*Run
	path     string
}

func New(repo policy.Repository, a analysis.Analyzer) *Server {
	return &Server{repo: repo, analyzer: a, runs: map[string]*Run{}}
}
func (s *Server) Routes() *echo.Echo {
	e := echo.New()
	e.Use(middleware.Recover())
	e.Use(middleware.CORS("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"))
	e.GET("/health", func(c *echo.Context) error { return c.JSON(http.StatusOK, map[string]string{"status": "ok"}) })
	e.POST("/api/runs", s.create)
	e.GET("/api/runs", s.list)
	e.GET("/api/runs/:id", s.get)
	e.POST("/api/runs/:id/review", s.review)
	e.POST("/api/runs/:id/mobilize", s.mobilize)
	return e
}
func (s *Server) list(c *echo.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	runs := make([]*Run, 0, len(s.runs))
	for _, r := range s.runs {
		runs = append(runs, r)
	}
	return c.JSON(http.StatusOK, runs)
}
func (s *Server) create(c *echo.Context) error {
	var body struct {
		Query string `json:"query"`
	}
	if err := c.Bind(&body); err != nil || strings.TrimSpace(body.Query) == "" || len(body.Query) > 2000 {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "query is required and must be at most 2000 characters"})
	}
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return c.JSON(500, map[string]string{"error": "could not create run"})
	}
	id := hex.EncodeToString(b)
	run := &Run{ID: id, Query: strings.TrimSpace(body.Query), Status: "queued", Stage: "queued", Findings: []analysis.Finding{}, Errors: []string{}, CreatedAt: time.Now().UTC()}
	s.mu.Lock()
	s.runs[id] = run
	if err := s.saveLocked(); err != nil {
		delete(s.runs, id)
		s.mu.Unlock()
		log.Printf("save run: %v", err)
		return c.JSON(500, map[string]string{"error": "could not persist run"})
	}
	s.mu.Unlock()
	go s.execute(id)
	return c.JSON(http.StatusAccepted, runResponse(id))
}
func runResponse(id string) map[string]string {
	return map[string]string{"id": id, "status": "queued", "status_url": "/api/runs/" + id}
}
func (s *Server) execute(id string) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	s.mu.Lock()
	r := s.runs[id]
	r.Status = "running"
	r.Stage = "retrieving"
	s.saveWorkerLocked()
	query := r.Query
	s.mu.Unlock()
	provisions, err := s.repo.Search(ctx, query, 20)
	if err != nil {
		s.fail(id, err)
		return
	}
	s.mu.Lock()
	r.Retrieved = len(provisions)
	r.Stage = "auditing_and_drafting"
	s.saveWorkerLocked()
	s.mu.Unlock()
	for _, p := range provisions {
		if err := ctx.Err(); err != nil {
			s.fail(id, err)
			return
		}
		f, err := s.analyzer.Analyze(ctx, query, p)
		s.mu.Lock()
		r.Reviewed++
		if err != nil {
			r.Errors = append(r.Errors, p.ID+": "+err.Error())
		} else if f != nil {
			r.Findings = append(r.Findings, *f)
		}
		s.saveWorkerLocked()
		s.mu.Unlock()
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(r.Errors) > 0 {
		if r.Reviewed == len(r.Errors) {
			r.Status = "failed"
		} else {
			r.Status = "completed_with_errors"
		}
	} else {
		r.Status = "completed"
	}
	r.Stage = "done"
	s.saveWorkerLocked()
}
func (s *Server) saveWorkerLocked() {
	if err := s.saveLocked(); err != nil {
		log.Printf("persist run state: %v", err)
	}
}
func (s *Server) fail(id string, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	r := s.runs[id]
	r.Status = "failed"
	r.Stage = "done"
	r.Errors = append(r.Errors, err.Error())
	s.saveWorkerLocked()
}
func (s *Server) get(c *echo.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.runs[c.Param("id")]
	if !ok {
		return c.JSON(404, map[string]string{"error": "run not found"})
	}
	return c.JSON(200, r)
}
func (s *Server) review(c *echo.Context) error {
	var body struct {
		FindingID string `json:"finding_id"`
	}
	if err := c.Bind(&body); err != nil || body.FindingID == "" {
		return c.JSON(400, map[string]string{"error": "finding_id is required"})
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.runs[c.Param("id")]
	if !ok {
		return c.JSON(404, map[string]string{"error": "run not found"})
	}
	if r.Status != "completed" && r.Status != "completed_with_errors" {
		return c.JSON(409, map[string]string{"error": "run is not complete"})
	}
	for _, f := range r.Findings {
		if f.ID == body.FindingID {
			previous := r.SelectedFindingID
			r.SelectedFindingID = f.ID
			if err := s.saveLocked(); err != nil {
				r.SelectedFindingID = previous
				log.Printf("save review: %v", err)
				return c.JSON(500, map[string]string{"error": "could not persist review"})
			}
			return c.JSON(200, map[string]string{"selected_finding_id": f.ID, "status": "approved"})
		}
	}
	return c.JSON(404, map[string]string{"error": "finding not found"})
}
func (s *Server) mobilize(c *echo.Context) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.runs[c.Param("id")]
	if !ok {
		return c.JSON(404, map[string]string{"error": "run not found"})
	}
	if r.SelectedFindingID == "" {
		return c.JSON(409, map[string]string{"error": "select a finding in review first"})
	}
	for _, f := range r.Findings {
		if f.ID == r.SelectedFindingID {
			return c.JSON(200, map[string]any{"status": "simulated", "message": "Handoff prepared; no calls were placed.", "run_id": r.ID, "query": r.Query, "finding": f})
		}
	}
	return errors.New("selected finding missing")
}
