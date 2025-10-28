import os, json, datetime
from bot.core.session_logger import SessionLogger

class StateManager:
    def __init__(self, state_file="reports/logs/last_state.json"):
        self.state_file = state_file
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

        # initialize default state before anything else
        self.state = {
            "last_cycle": None,
            "total_cycles": 0,
            "last_update": datetime.datetime.now().isoformat(),
            "notes": "initialized"
        }

        # safe logger setup
        try:
            self.logger = SessionLogger()
        except Exception:
            # fallback: dummy logger in case SessionLogger already active
            class DummyLogger:
                def log_event(self, *args, **kwargs): pass
            self.logger = DummyLogger()

        # try to load existing state file if it exists
        self.load_state()

    def load_state(self):
        """Load previous state if it exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                self.logger.log_event("STATE_LOAD", "Previous state loaded", self.state)
                return self.state
            except Exception as e:
                self.logger.log_event("STATE_LOAD_ERROR", f"Failed to load state: {e}")
        else:
            self.save_state()
            self.logger.log_event("STATE_INIT", "Created new state file")
        return self.state

    def save_state(self, new_data=None):
        """Save or update the state file."""
        if new_data:
            self.state.update(new_data)
        self.state["last_update"] = datetime.datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        self.logger.log_event("STATE_SAVE", "State updated", self.state)

    def record_cycle(self, cycle_no, data=None):
        """Record the result of each completed cycle."""
        self.state["last_cycle"] = cycle_no
        self.state["total_cycles"] = self.state.get("total_cycles", 0) + 1
        self.state["last_update"] = datetime.datetime.now().isoformat()
        if data:
            self.state["summary"] = data
        self.save_state()
