package policy

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"
)

// DefaultHydraQuery is a provisional graph contract; override for the seed schema.
// IDs are projected into a separate alias because HydraDB's id is a vertex ID.
const DefaultHydraQuery = `MATCH (p:Provision) RETURN p.id AS id, p.title AS title, p.citation AS citation, p.jurisdiction AS jurisdiction, p.topic AS topic, p.text AS text, p.source_url AS source_url, p.effective_date AS effective_date LIMIT 500`

type Hydra struct {
	BaseURL, Token, GraphID, CellID, Namespace, Query string
	Client                                            *http.Client
}

func (h Hydra) Search(ctx context.Context, query string, limit int) ([]Provision, error) {
	if h.BaseURL == "" || h.Token == "" || h.GraphID == "" || h.CellID == "" {
		return nil, fmt.Errorf("HydraDB URL, token, graph ID and cell ID are required")
	}
	cypher := h.Query
	if cypher == "" {
		cypher = DefaultHydraQuery
	}
	payload, err := json.Marshal(map[string]any{"cell_id": h.CellID, "query": cypher})
	if err != nil {
		return nil, err
	}
	endpoint := strings.TrimRight(h.BaseURL, "/") + "/v1/graphs/" + url.PathEscape(h.GraphID) + "/query"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+h.Token)
	req.Header.Set("Content-Type", "application/json")
	if h.Namespace != "" {
		req.Header.Set("X-Graph-Namespace", h.Namespace)
	}
	client := h.Client
	if client == nil {
		client = &http.Client{Timeout: 30 * time.Second}
	}
	res, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("HydraDB request: %w", err)
	}
	defer res.Body.Close()
	b, err := io.ReadAll(io.LimitReader(res.Body, 16<<20))
	if err != nil {
		return nil, err
	}
	if res.StatusCode < 200 || res.StatusCode >= 300 {
		return nil, fmt.Errorf("HydraDB returned HTTP %d: %s", res.StatusCode, strings.TrimSpace(string(b)))
	}
	var decoded struct {
		Columns []string `json:"columns"`
		Rows    [][]struct {
			Type  string          `json:"type"`
			Value json.RawMessage `json:"value"`
		} `json:"rows"`
		NextCursor *string `json:"next_cursor"`
		Error      *struct {
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(b, &decoded); err != nil {
		return nil, fmt.Errorf("invalid HydraDB response: %w", err)
	}
	if decoded.Error != nil {
		return nil, fmt.Errorf("HydraDB query failed: %s", decoded.Error.Message)
	}
	if decoded.Rows == nil {
		return nil, fmt.Errorf("HydraDB response missing rows")
	}
	if decoded.NextCursor != nil {
		return nil, fmt.Errorf("HydraDB returned paginated results; narrow the query before analysis")
	}
	index := map[string]int{}
	for i, name := range decoded.Columns {
		index[name] = i
	}
	for _, name := range []string{"id", "title", "citation", "jurisdiction", "topic", "text", "source_url", "effective_date"} {
		if _, ok := index[name]; !ok {
			return nil, fmt.Errorf("HydraDB query missing %q column", name)
		}
	}
	provisions := make([]Provision, 0, len(decoded.Rows))
	for _, row := range decoded.Rows {
		field := func(name string) (string, error) {
			i := index[name]
			if i >= len(row) {
				return "", fmt.Errorf("short HydraDB row")
			}
			cell := row[i]
			if cell.Type == "null" || len(cell.Value) == 0 {
				return "", nil
			}
			var s string
			if json.Unmarshal(cell.Value, &s) == nil {
				return s, nil
			}
			var n json.Number
			if json.Unmarshal(cell.Value, &n) == nil {
				return n.String(), nil
			}
			return "", fmt.Errorf("unsupported %s cell type %s", name, cell.Type)
		}
		var p Provision
		fields := []struct {
			name string
			dst  *string
		}{{"id", &p.ID}, {"title", &p.Title}, {"citation", &p.Citation}, {"jurisdiction", &p.Jurisdiction}, {"topic", &p.Topic}, {"text", &p.Text}, {"source_url", &p.SourceURL}, {"effective_date", &p.EffectiveDate}}
		for _, f := range fields {
			v, err := field(f.name)
			if err != nil {
				return nil, err
			}
			*f.dst = v
		}
		if p.ID == "" || p.Text == "" {
			return nil, fmt.Errorf("HydraDB provision is missing id or text")
		}
		provisions = append(provisions, p)
	}
	// Lexical ranking is a temporary stand-in for graph/semantic retrieval. It
	// never claims to have searched beyond the capped candidate query.
	words := strings.Fields(strings.ToLower(query))
	type scored struct {
		p     Provision
		score int
	}
	var matches []scored
	for _, p := range provisions {
		hay := strings.ToLower(p.Title + " " + p.Jurisdiction + " " + p.Topic + " " + p.Text)
		score := 0
		for _, w := range words {
			w = strings.Trim(w, ",.?!:;\"'()")
			if len(w) > 3 && strings.Contains(hay, w) {
				score++
			}
		}
		if score > 0 {
			matches = append(matches, scored{p, score})
		}
	}
	sort.SliceStable(matches, func(i, j int) bool { return matches[i].score > matches[j].score })
	if limit < 0 {
		limit = 0
	}
	if len(matches) > limit {
		matches = matches[:limit]
	}
	out := make([]Provision, len(matches))
	for i, m := range matches {
		out[i] = m.p
	}
	return out, nil
}
