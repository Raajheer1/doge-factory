package policy

import (
	"context"
	"encoding/json"
	"os"
	"strings"
)

// Provision is the interface contract between retrieval and analysis. Fixture
// provisions are synthetic and must not be presented as enacted law.
type Provision struct {
	ID             string       `json:"id"`
	Title          string       `json:"title"`
	Citation       string       `json:"citation"`
	Jurisdiction   string       `json:"jurisdiction"`
	Topic          string       `json:"topic"`
	Text           string       `json:"text"`
	SourceURL      string       `json:"source_url,omitempty"`
	EffectiveDate  string       `json:"effective_date,omitempty"`
	IssuingAgency  string       `json:"issuing_agency,omitempty"`
	DocumentType   string       `json:"document_type,omitempty"`
	SourceStatus   string       `json:"source_status,omitempty"`
	RelatedContext []string     `json:"related_context,omitempty"`
	Comparisons    []Comparison `json:"comparisons,omitempty"`
	Synthetic      bool         `json:"synthetic"`
}

// Comparison contains peer-jurisdiction material supplied by the repository.
// A difference alone does not establish that the alternative is effective.
type Comparison struct {
	ID           string `json:"id"`
	Jurisdiction string `json:"jurisdiction"`
	Citation     string `json:"citation"`
	SourceURL    string `json:"source_url"`
	Text         string `json:"text"`
	Context      string `json:"context,omitempty"`
}

type Repository interface {
	Search(context.Context, string, int) ([]Provision, error)
}

type Fixtures struct{ Provisions []Provision }

func (f Fixtures) Search(ctx context.Context, query string, limit int) ([]Provision, error) {
	// This is deliberately a minimal placeholder, not a graph search engine.
	words := strings.Fields(strings.ToLower(query))
	result := make([]Provision, 0)
	for _, p := range f.Provisions {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		hay := strings.ToLower(p.Title + " " + p.Jurisdiction + " " + p.Topic + " " + p.Text)
		for _, w := range words {
			if len(w) > 3 && strings.Contains(hay, strings.Trim(w, ",.?!")) {
				result = append(result, p)
				break
			}
		}
		if len(result) >= limit {
			break
		}
	}
	return result, nil
}
func Load(path string) (Fixtures, error) {
	if path == "" {
		return Fixtures{[]Provision{{ID: "demo-income-verification", Title: "Synthetic housing income verification rule", Citation: "DEMO ONLY — not an enacted provision", Jurisdiction: "Iowa", Topic: "housing healthcare income verification", Text: "An applicant must submit a paper pay stub in person, and an employee must manually verify income by telephone. The applicant may appeal a determination.", Synthetic: true}}}, nil
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return Fixtures{}, err
	}
	var p []Provision
	if err = json.Unmarshal(b, &p); err != nil {
		return Fixtures{}, err
	}
	return Fixtures{p}, nil
}
