CLAUDE_DIR := $(HOME)/.claude

COMMAND_FILES := $(wildcard commands/*.md)
SHARED_FILES := $(wildcard shared/*.md)

.PHONY: deploy diff status

deploy:
	@echo "Deploying commands to $(CLAUDE_DIR)/commands/"
	@mkdir -p $(CLAUDE_DIR)/commands
	@cp -v $(COMMAND_FILES) $(CLAUDE_DIR)/commands/
	@echo ""
	@echo "Deploying shared files to $(CLAUDE_DIR)/shared/"
	@mkdir -p $(CLAUDE_DIR)/shared
	@cp -v $(SHARED_FILES) $(CLAUDE_DIR)/shared/
	@echo ""
	@echo "Deploy complete."

diff:
	@echo "=== Commands ==="
	@for f in $(COMMAND_FILES); do \
		echo "--- $$f vs $(CLAUDE_DIR)/$$f ---"; \
		diff -u "$$f" "$(CLAUDE_DIR)/$$f" 2>/dev/null || true; \
	done
	@echo ""
	@echo "=== Shared ==="
	@for f in $(SHARED_FILES); do \
		echo "--- $$f vs $(CLAUDE_DIR)/$$f ---"; \
		diff -u "$$f" "$(CLAUDE_DIR)/$$f" 2>/dev/null || true; \
	done

status:
	@echo "Sync status (repo vs ~/.claude):"
	@all_synced=true; \
	for f in $(COMMAND_FILES) $(SHARED_FILES); do \
		if diff -q "$$f" "$(CLAUDE_DIR)/$$f" > /dev/null 2>&1; then \
			echo "  ✓ $$f"; \
		else \
			echo "  ✗ $$f (diverged)"; \
			all_synced=false; \
		fi; \
	done; \
	if $$all_synced; then \
		echo "All files in sync."; \
	else \
		echo "Run 'make diff' to see changes, 'make deploy' to sync."; \
	fi
