package api

import (
	"context"

	"doge-factory/internal/analysis"
	"doge-factory/internal/policy"
)

// MobilizeHandoff is the mobilize.v1 document; see docs/mobilize-handoff.md.
type MobilizeHandoff struct {
	Version string          `json:"version"`
	RunID   string          `json:"run_id,omitempty"`
	Query   string          `json:"query,omitempty"`
	Policy  HandoffPolicy   `json:"policy"`
	Change  HandoffChange   `json:"change"`
	Impact  HandoffImpact   `json:"impact"`
	People  []policy.Person `json:"people"`
	Notes   string          `json:"notes,omitempty"`
}

type HandoffJurisdiction struct {
	Name  string `json:"name"`
	Level string `json:"level"`
}

type HandoffPolicy struct {
	ID            string              `json:"id"`
	Title         string              `json:"title"`
	SpokenTitle   string              `json:"spoken_title"`
	Citation      string              `json:"citation,omitempty"`
	Jurisdiction  HandoffJurisdiction `json:"jurisdiction"`
	IssuingAgency string              `json:"issuing_agency,omitempty"`
	SourceURL     string              `json:"source_url,omitempty"`
	EffectiveDate string              `json:"effective_date,omitempty"`
	Synthetic     bool                `json:"synthetic"`
}

type HandoffChange struct {
	Summary       string   `json:"summary"`
	Barrier       string   `json:"barrier"`
	EvidenceQuote string   `json:"evidence_quote,omitempty"`
	ProposedText  string   `json:"proposed_text,omitempty"`
	Justification string   `json:"justification,omitempty"`
	Safeguards    []string `json:"safeguards"`
	Uncertainties []string `json:"uncertainties"`
}

type HandoffImpact struct {
	EstimatedAnnualSavings *float64 `json:"estimated_annual_savings"` // nil = not measured
	SavingsBasis           string   `json:"savings_basis,omitempty"`
	AffectedGroups         []string `json:"affected_groups"`
}

// handoffResponse adds the earlier simulated-handoff fields so existing
// clients keep working; mobilize.v1 consumers ignore extra fields.
type handoffResponse struct {
	MobilizeHandoff
	Status  string           `json:"status"`
	Message string           `json:"message"`
	Finding analysis.Finding `json:"finding"`
}

type briefer interface {
	Brief(context.Context, analysis.Finding) (analysis.HandoffBrief, error)
}

func buildHandoff(r Run, f analysis.Finding, b analysis.HandoffBrief, people []policy.Person) MobilizeHandoff {
	p := f.Provision
	jurisdiction := HandoffJurisdiction{Name: p.Jurisdiction, Level: "state"}
	if p.Jurisdiction == "" || p.Jurisdiction == "United States" {
		jurisdiction = HandoffJurisdiction{Name: "United States", Level: "federal"}
	}
	// Drop entries mobilize.v1 would reject: officials need a title, lobbyists a client.
	callable := make([]policy.Person, 0, len(people))
	targets := 0
	for _, person := range people {
		if (person.Type == "official" && person.Title == "") || (person.Type == "lobbyist" && len(person.Clients) == 0) {
			continue
		}
		if person.Type != "organization" {
			targets++
		}
		callable = append(callable, person)
	}
	notes := ""
	if targets == 0 {
		notes = "No officials or lobbyists are linked to this policy in the graph yet."
	}
	nonNil := func(s []string) []string {
		if s == nil {
			return []string{}
		}
		return s
	}
	return MobilizeHandoff{
		Version: "mobilize.v1", RunID: r.ID, Query: r.Query,
		Policy: HandoffPolicy{ID: p.ID, Title: p.Title, SpokenTitle: b.SpokenTitle, Citation: p.Citation, Jurisdiction: jurisdiction, IssuingAgency: p.IssuingAgency, SourceURL: p.SourceURL, EffectiveDate: p.EffectiveDate, Synthetic: p.Synthetic},
		Change: HandoffChange{Summary: b.Summary, Barrier: f.Barrier, EvidenceQuote: f.SourcePassage, ProposedText: f.Amendment, Justification: f.Justification, Safeguards: nonNil(f.Safeguards), Uncertainties: nonNil(f.Uncertainties)},
		Impact: HandoffImpact{AffectedGroups: b.AffectedGroups},
		People: callable,
		Notes:  notes,
	}
}
