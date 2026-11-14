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

// Person is a public actor connected to a policy document in the graph.
// Relevance uses the mobilize.v1 vocabulary (docs/mobilize-handoff.md).
type Person struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	Type         string   `json:"type"`
	Title        string   `json:"title,omitempty"`
	Role         string   `json:"role,omitempty"`
	Organization string   `json:"organization,omitempty"`
	State        string   `json:"state,omitempty"`
	District     string   `json:"district,omitempty"`
	Clients      []string `json:"clients,omitempty"`
	Relevance    string   `json:"relevance"`
	VerifiedAt   string   `json:"verified_at"`
	SourceURL    string   `json:"source_url,omitempty"`
}

const actorFields = "a.id AS id, a.name AS name, a.type AS type, a.title AS title, a.role AS role, a.organization AS organization, a.state AS state, a.district AS district, a.verified_at AS verified_at, a.source_url AS source_url"

// peopleQueries return actors tied to one document: direct, sourced links;
// the administering agency; and officials who work for it.
var peopleQueries = []string{
	"MATCH (a:Actor)-[r:HAS_AUTHORITY_OVER|LOBBIED_ON|RELEVANT_TO]->(d:PolicyDocument {id: $id}) OPTIONAL MATCH (a)-[:REPRESENTS]->(c:Actor) RETURN " + actorFields + ", type(r) AS rel, r.relevance AS relevance, r.source_url AS rel_source, collect(c.name) AS clients",
	"MATCH (a:Actor)-[r:ADMINISTERS]->(d:PolicyDocument {id: $id}) RETURN " + actorFields + ", 'ADMINISTERS' AS rel, '' AS relevance, r.source_url AS rel_source, [] AS clients",
	"MATCH (a:Actor)-[:WORKS_FOR]->(g:Actor)-[r:ADMINISTERS]->(d:PolicyDocument {id: $id}) RETURN " + actorFields + ", 'ADMINISTERS' AS rel, '' AS relevance, r.source_url AS rel_source, [] AS clients",
}

// Strongest claim first; the order people are handed to Mobilize.
var relevanceRank = map[string]int{"authority_over_document": 0, "lobbied_on_document": 1, "committee_jurisdiction": 2, "administers": 3, "represents_affected_client": 4, "other": 5}

// People lists actors connected to a document, most relevant first. A
// collection without actors returns an empty list, not an error.
func (h BYOG) People(ctx context.Context, collection, documentID string) ([]Person, error) {
	byID := map[string]Person{}
	for _, cypher := range peopleQueries {
		rows, err := h.query(ctx, collection, cypher, map[string]any{"id": documentID})
		if err != nil {
			return nil, err
		}
		for _, row := range rows {
			get := func(k string) string { s, _ := row[k].(string); return s }
			p := Person{ID: get("id"), Name: get("name"), Type: get("type"), Title: get("title"), Role: get("role"), Organization: get("organization"), State: get("state"), District: get("district"), VerifiedAt: get("verified_at"), SourceURL: get("source_url")}
			switch get("rel") {
			case "HAS_AUTHORITY_OVER":
				p.Relevance = "authority_over_document"
			case "LOBBIED_ON":
				p.Relevance = "lobbied_on_document"
			case "ADMINISTERS":
				p.Relevance = "administers"
			default:
				p.Relevance = get("relevance")
			}
			if _, ok := relevanceRank[p.Relevance]; !ok {
				p.Relevance = "other"
			}
			if clients, ok := row["clients"].([]any); ok {
				for _, c := range clients {
					if s, ok := c.(string); ok && s != "" {
						p.Clients = append(p.Clients, s)
					}
				}
			}
			if p.SourceURL == "" {
				p.SourceURL = get("rel_source")
			}
			if p.VerifiedAt == "" {
				p.VerifiedAt = "unverified"
			}
			if p.ID == "" || p.Name == "" {
				continue
			}
			if prev, ok := byID[p.ID]; ok && relevanceRank[prev.Relevance] <= relevanceRank[p.Relevance] {
				continue
			}
			byID[p.ID] = p
		}
	}
	people := make([]Person, 0, len(byID))
	for _, p := range byID {
		people = append(people, p)
	}
	sort.SliceStable(people, func(i, j int) bool {
		if ri, rj := relevanceRank[people[i].Relevance], relevanceRank[people[j].Relevance]; ri != rj {
			return ri < rj
		}
		return people[i].ID < people[j].ID
	})
	return people, nil
}

func (h BYOG) query(ctx context.Context, collection, cypher string, params map[string]any) ([]map[string]any, error) {
	payload, err := json.Marshal(map[string]any{"database": h.Database, "collection": collection, "query": cypher, "params": params})
	if err != nil {
		return nil, err
	}
	req, err := http.NewRequestWithContext(ctx, "POST", strings.TrimRight(h.BaseURL, "/")+"/byog/query", bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+h.Key)
	req.Header.Set("Content-Type", "application/json")
	resp, err := (&http.Client{Timeout: 30 * time.Second}).Do(req)
	if err != nil {
		return nil, fmt.Errorf("people query: %w", err)
	}
	defer resp.Body.Close()
	var result struct {
		Success bool             `json:"success"`
		Data    []map[string]any `json:"data"`
		Error   json.RawMessage  `json:"error"`
	}
	if err = json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("people query: %w", err)
	}
	if resp.StatusCode != 200 || !result.Success {
		return nil, fmt.Errorf("people query returned HTTP %d: %s", resp.StatusCode, result.Error)
	}
	return result.Data, nil
}
