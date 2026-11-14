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

// fallbackQueries find people for a document with no direct links: the agency
// that issued it, and the agency's staff.
var fallbackQueries = []string{
	"MATCH (d:PolicyDocument {id: $id}) MATCH (a:Actor {type: 'organization'}) WHERE d.issuing_agency IS NOT NULL AND toLower(a.name) = toLower(d.issuing_agency) RETURN " + actorFields + ", 'ADMINISTERS' AS rel, '' AS relevance, '' AS rel_source, [] AS clients",
	"MATCH (d:PolicyDocument {id: $id}) MATCH (a:Actor)-[:WORKS_FOR]->(g:Actor) WHERE d.issuing_agency IS NOT NULL AND toLower(g.name) = toLower(d.issuing_agency) RETURN " + actorFields + ", 'ADMINISTERS' AS rel, '' AS relevance, '' AS rel_source, [] AS clients",
}

// committeeMembers caps how many committee members a fallback hands to Mobilize.
const committeeMembers = 4

// Strongest claim first; the order people are handed to Mobilize.
var relevanceRank = map[string]int{"authority_over_document": 0, "lobbied_on_document": 1, "committee_jurisdiction": 2, "administers": 3, "represents_affected_client": 4, "other": 5}

// People lists actors connected to a document, most relevant first. A
// collection without actors returns an empty list, not an error.
func (h BYOG) People(ctx context.Context, collection, documentID string) ([]Person, error) {
	byID := map[string]Person{}
	if err := h.collect(ctx, collection, documentID, peopleQueries, byID); err != nil {
		return nil, err
	}
	// Many collections link actors to committees and agencies rather than to
	// documents; fall back to those so a document still has someone to call.
	if len(byID) == 0 {
		if err := h.collect(ctx, collection, documentID, fallbackQueries, byID); err != nil {
			return nil, err
		}
		if err := h.committeeFallback(ctx, collection, documentID, byID); err != nil {
			return nil, err
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

// committeeFallback adds members of the committees whose names share the most
// words with the document (title, agency, topic), up to committeeMembers.
func (h BYOG) committeeFallback(ctx context.Context, collection, documentID string, byID map[string]Person) error {
	docs, err := h.query(ctx, collection, "MATCH (d:PolicyDocument {id: $id}) RETURN coalesce(d.title, '') + ' ' + coalesce(d.issuing_agency, '') + ' ' + coalesce(toString(d.topics), '') AS text", map[string]any{"id": documentID})
	if err != nil || len(docs) == 0 {
		return err
	}
	text, _ := docs[0]["text"].(string)
	words := map[string]bool{}
	for _, w := range strings.FieldsFunc(strings.ToLower(text), func(r rune) bool { return !('a' <= r && r <= 'z') }) {
		if len(w) >= 5 {
			words[w] = true
		}
	}
	committees, err := h.query(ctx, collection, "MATCH (:Actor {type: 'official'})-[:MEMBER_OF]->(c:Actor) RETURN DISTINCT c.id AS id, c.name AS name", map[string]any{})
	if err != nil {
		return err
	}
	type scored struct {
		id    string
		score int
	}
	var ranked []scored
	for _, c := range committees {
		id, _ := c["id"].(string)
		name, _ := c["name"].(string)
		score := 0
		for _, w := range strings.FieldsFunc(strings.ToLower(name), func(r rune) bool { return !('a' <= r && r <= 'z') }) {
			if words[w] {
				score++
			}
		}
		if score > 0 && id != "" {
			ranked = append(ranked, scored{id, score})
		}
	}
	sort.SliceStable(ranked, func(i, j int) bool {
		return ranked[i].score > ranked[j].score || (ranked[i].score == ranked[j].score && ranked[i].id < ranked[j].id)
	})
	added := 0
	for _, c := range ranked {
		rows, err := h.query(ctx, collection, "MATCH (a:Actor {type: 'official'})-[:MEMBER_OF]->(c:Actor {id: $committee}) RETURN "+actorFields+", 'COMMITTEE' AS rel, 'committee_jurisdiction' AS relevance, c.source_url AS rel_source, [] AS clients ORDER BY a.id LIMIT $limit", map[string]any{"committee": c.id, "limit": committeeMembers - added})
		if err != nil {
			return err
		}
		before := len(byID)
		addRows(rows, byID)
		if added += len(byID) - before; added >= committeeMembers {
			break
		}
	}
	return nil
}

func (h BYOG) collect(ctx context.Context, collection, documentID string, queries []string, byID map[string]Person) error {
	for _, cypher := range queries {
		rows, err := h.query(ctx, collection, cypher, map[string]any{"id": documentID})
		if err != nil {
			return err
		}
		addRows(rows, byID)
	}
	return nil
}

func addRows(rows []map[string]any, byID map[string]Person) {
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
		if p.Type == "official" && p.Title == "" {
			p.Title = p.Role // some sources only record the office as a role ("Senator")
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
