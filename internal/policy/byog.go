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
	if collection != "housing" && collection != "healthcare" {
		return nil, fmt.Errorf("invalid collection")
	}
	payload, _ := json.Marshal(map[string]any{"database": h.Database, "collection": collection, "query": "MATCH (d:PolicyDocument) RETURN d.id AS id, d.title AS title, d.citation AS citation, d.text AS text, d.source_url AS source_url, d.topics AS topic, d.issuing_agency AS issuing_agency, d.source_snapshot AS snapshot LIMIT 10000", "params": map[string]any{}})
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
		p := Provision{ID: get("id"), Title: get("title"), Citation: get("citation"), Text: get("text"), SourceURL: get("source_url"), Topic: get("topic"), IssuingAgency: get("issuing_agency"), Jurisdiction: "", RelatedContext: []string{"Source snapshot: " + get("snapshot")}}
		parts := strings.Split(p.ID, ":")
		if len(parts) >= 2 && (parts[0] == "qap" || parts[0] == "healthcare-state-plan") {
			p.Jurisdiction = stateNames[parts[1]]
		} else if strings.HasPrefix(p.ID, "ecfr:") || strings.HasPrefix(p.ID, "usc:") {
			p.Jurisdiction = "United States"
		}
		if p.ID == "" || p.Text == "" {
			continue
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
