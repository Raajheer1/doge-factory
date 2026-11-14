package main

import (
	"log"
	"os"

	"doge-factory/internal/analysis"
	"doge-factory/internal/api"
	"doge-factory/internal/policy"
)

func main() {
	key := os.Getenv("AI_GATEWAY_API_KEY")
	if key == "" {
		log.Fatal("AI_GATEWAY_API_KEY is required")
	}
	gateway := analysis.NewGateway(key, os.Getenv("AI_GATEWAY_BASE_URL"), os.Getenv("AI_GATEWAY_MODEL"))
	var repo policy.Repository
	if os.Getenv("HYDRADB_API_KEY") != "" {
		base := os.Getenv("HYDRADB_BASE_URL")
		if base == "" {
			base = "https://api.hydradb.com"
		}
		db := os.Getenv("HYDRADB_DATABASE_ID")
		if db == "" {
			db = "doge-factory"
		}
		repo = policy.BYOG{BaseURL: base, Database: db, Key: os.Getenv("HYDRADB_API_KEY"), Expand: gateway.SearchTerms}
	} else if os.Getenv("HYDRA_URL") != "" {
		graph, cell := os.Getenv("HYDRA_GRAPH_ID"), os.Getenv("HYDRA_CELL_ID")
		if graph == "" {
			graph = "default"
		}
		if cell == "" {
			cell = "cell-0"
		}
		if os.Getenv("HYDRA_TOKEN") == "" {
			log.Fatal("HYDRA_TOKEN is required with HYDRA_URL")
		}
		query := ""
		if path := os.Getenv("HYDRA_QUERY_FILE"); path != "" {
			data, err := os.ReadFile(path)
			if err != nil {
				log.Fatal(err)
			}
			query = string(data)
		}
		repo = policy.Hydra{BaseURL: os.Getenv("HYDRA_URL"), Token: os.Getenv("HYDRA_TOKEN"), GraphID: graph, CellID: cell, Namespace: os.Getenv("HYDRA_NAMESPACE"), Query: query}
	} else {
		fixtures, err := policy.Load(os.Getenv("POLICY_FIXTURES_FILE"))
		if err != nil {
			log.Fatal(err)
		}
		repo = fixtures
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = "127.0.0.1:8080"
	}
	server := api.New(repo, gateway)
	path := os.Getenv("RUNS_FILE")
	if path == "" {
		path = "data/runs.json"
	}
	if err := server.EnablePersistence(path); err != nil {
		log.Fatal(err)
	}
	log.Printf("listening on %s", addr)
	if err := server.Routes().Start(addr); err != nil {
		log.Fatal(err)
	}
}
