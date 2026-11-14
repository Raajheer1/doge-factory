package policy

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"
)

// BYOG reads hosted policy collections.
var stateNames = map[string]string{"al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas", "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii", "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas", "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland", "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi", "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada", "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York", "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma", "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island", "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas", "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington", "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming", "dc": "District of Columbia"}

type BYOG struct {
	BaseURL, Database, Key string
	Expand                 func(context.Context, string) ([]string, error)
}

func (h BYOG) Search(ctx context.Context, query string, limit int) ([]Provision, error) {
	return h.SearchCollection(ctx, query, limit, "healthcare")
}

func (h BYOG) SearchCollection(ctx context.Context, query string, limit int, collection string) ([]Provision, error) {
	if collection != "housing" && collection != "healthcare" && collection != "other" {
		return nil, fmt.Errorf("invalid collection")
	}
	payload, _ := json.Marshal(map[string]any{"database": h.Database, "collection": collection, "query": "MATCH (d:PolicyDocument) WHERE coalesce(d.document_type, '') <> 'evidence' OPTIONAL MATCH (j:Jurisdiction)-[:ISSUED]->(d) OPTIONAL MATCH (e:PolicyDocument)-[:CITES]->(d) RETURN d.id AS id, d.title AS title, d.citation AS citation, d.text AS text, d.source_url AS source_url, d.topics AS topic, d.issuing_agency AS issuing_agency, d.document_type AS document_type, d.status AS source_status, d.source_snapshot AS snapshot, j.name AS jurisdiction, collect(e.text) AS evidence LIMIT 10000", "params": map[string]any{}})
	req, err := http.NewRequestWithContext(ctx, "POST", strings.TrimRight(h.BaseURL, "/")+"/byog/query", bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+h.Key)
	req.Header.Set("Content-Type", "application/json")
	resp, err := (&http.Client{Timeout: 90 * time.Second}).Do(req)
	if err != nil {
		return nil, fmt.Errorf("collection retrieval: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("collection retrieval returned HTTP %d", resp.StatusCode)
	}
	var result struct {
		Success bool                                                                     `json:"success"`
		Data    []struct{ ID, Title, Citation, Text, SourceURL, Topic, Snapshot string } `json:"data"`
		Error   json.RawMessage                                                          `json:"error"`
	}
	// Explicit mapping is needed for snake-case source fields.
	var raw struct {
		Success bool             `json:"success"`
		Data    []map[string]any `json:"data"`
		Error   json.RawMessage  `json:"error"`
	}
	if err = json.NewDecoder(resp.Body).Decode(&raw); err != nil {
		return nil, err
	}
	result.Success = raw.Success
	result.Error = raw.Error
	if !result.Success {
		return nil, fmt.Errorf("collection query failed: %s", result.Error)
	}
	if raw.Data == nil {
		return nil, fmt.Errorf("collection query returned no data array")
	}
	if len(raw.Data) >= 10000 {
		return nil, fmt.Errorf("collection search exceeds retrieval limit")
	}
	expanded := []string{}
	if h.Expand != nil {
		var expandErr error
		expanded, expandErr = h.Expand(ctx, query)
		if expandErr != nil {
			return nil, fmt.Errorf("search term expansion: %w", expandErr)
		}
	}
	words := strings.FieldsFunc(strings.ToLower(query), func(r rune) bool { return !((r >= 'a' && r <= 'z') || (r >= '0' && r <= '9')) })
	queryWords := " " + strings.Join(words, " ") + " "
	requestedStates := map[string]bool{}
	for _, name := range stateNames {
		if strings.Contains(queryWords, " "+strings.ToLower(name)+" ") {
			requestedStates[name] = true
		}
	}
	terms := map[string]bool{}
	for _, w := range words {
		if len(w) > 3 {
			terms[w] = true
		}
	}
	for _, term := range expanded {
		term = strings.ToLower(strings.TrimSpace(term))
		if len(term) >= 4 && len(term) <= 120 {
			terms[term] = true
		}
	}
	if collection == "healthcare" && (strings.Contains(strings.ToLower(query), "record") || strings.Contains(strings.ToLower(query), "transfer")) {
		for _, w := range []string{"interoperability", "information blocking", "electronic health information", "disclosure", "exchange"} {
			terms[w] = true
		}
	}
	type ranked struct {
		p     Provision
		score int
	}
	var rankedDocs []ranked
	for _, d := range raw.Data {
		get := func(k string) string { s, _ := d[k].(string); return s }
		p := Provision{ID: get("id"), Title: get("title"), Citation: get("citation"), Text: get("text"), SourceURL: get("source_url"), Topic: get("topic"), IssuingAgency: get("issuing_agency"), DocumentType: get("document_type"), SourceStatus: get("source_status"), Jurisdiction: "", RelatedContext: []string{"Source snapshot: " + get("snapshot")}}
		// Evidence documents (cost and status figures) that cite this policy.
		if evidence, ok := d["evidence"].([]any); ok {
			for _, e := range evidence {
				if s, ok := e.(string); ok && s != "" {
					p.RelatedContext = append(p.RelatedContext, "Evidence: "+s)
				}
			}
		}
		parts := strings.Split(p.ID, ":")
		if len(parts) >= 2 && (parts[0] == "qap" || parts[0] == "healthcare-state-plan") {
			p.Jurisdiction = stateNames[parts[1]]
		} else if strings.HasPrefix(p.ID, "ecfr:") || strings.HasPrefix(p.ID, "usc:") {
			p.Jurisdiction = "United States"
		} else {
			p.Jurisdiction = get("jurisdiction")
		}
		if p.ID == "" || p.Text == "" {
			continue
		}
		// A single-state request should not be crowded out by unrelated state
		// plans. Keep federal and unknown-jurisdiction material as context.
		if len(requestedStates) == 1 && !requestedStates[p.Jurisdiction] {
			otherState := false
			for _, name := range stateNames {
				if p.Jurisdiction == name {
					otherState = true
					break
				}
			}
			if otherState {
				continue
			}
		}
		hay := strings.ToLower(p.Title + " " + p.Topic + " " + p.Text)
		score := 0
		if p.Jurisdiction != "" && p.Jurisdiction != "United States" && strings.Contains(strings.ToLower(query), strings.ToLower(p.Jurisdiction)) {
			score += 8
		}
		for w := range terms {
			if strings.Contains(hay, w) {
				score++
			}
		}
		// For income-verification research, favor passages that actually discuss
		// verification and employment rather than generic QAP boilerplate. Only
		// apply this boost when the user requested those concepts.
		goal := strings.ToLower(query)
		if strings.Contains(goal, "verif") && (strings.Contains(goal, "income") || strings.Contains(goal, "employ")) {
			text := strings.ToLower(p.Text)
			if strings.Contains(text, "verif") && (strings.Contains(text, "income") || strings.Contains(text, "employ")) {
				score += 8
				if strings.Contains(text, "employ") {
					score += 4
				}
				if strings.Contains(text, "telephone") || strings.Contains(text, "phone") || strings.Contains(text, "oral verification") {
					score += 3
				}
			}
		}
		if score > 0 {
			rankedDocs = append(rankedDocs, ranked{p, score})
		}
	}
	sort.SliceStable(rankedDocs, func(i, j int) bool {
		if rankedDocs[i].score == rankedDocs[j].score {
			return rankedDocs[i].p.ID < rankedDocs[j].p.ID
		}
		return rankedDocs[i].score > rankedDocs[j].score
	})
	if limit < 0 {
		limit = 0
	}
	if len(rankedDocs) > limit {
		rankedDocs = rankedDocs[:limit]
	}
	out := make([]Provision, 0, len(rankedDocs))
	for _, v := range rankedDocs {
		out = append(out, v.p)
	}
	return out, nil
}
