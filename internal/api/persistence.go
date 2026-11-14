package api

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// A single-process local store; writes replace the complete snapshot atomically.
func (s *Server) EnablePersistence(path string) error {
	if path == "" {
		return nil
	}
	s.path = path
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	if err = json.Unmarshal(data, &s.runs); err != nil {
		return fmt.Errorf("load runs: %w", err)
	}
	if s.runs == nil {
		s.runs = map[string]*Run{}
	}
	for _, r := range s.runs {
		if r.Status == "queued" || r.Status == "running" {
			r.Status = "failed"
			r.Stage = "done"
			r.Errors = append(r.Errors, "server stopped before analysis completed")
		}
	}
	return s.saveLocked()
}
func (s *Server) saveLocked() error {
	if s.path == "" {
		return nil
	}
	data, err := json.Marshal(s.runs)
	if err != nil {
		return err
	}
	dir := filepath.Dir(s.path)
	if err = os.MkdirAll(dir, 0700); err != nil {
		return err
	}
	f, err := os.CreateTemp(dir, ".runs-*")
	if err != nil {
		return err
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if err = f.Chmod(0600); err == nil {
		_, err = f.Write(data)
	}
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err != nil {
		return err
	}
	if closeErr != nil {
		return closeErr
	}
	return os.Rename(tmp, s.path)
}
