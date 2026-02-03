import logging
import sys
import importlib

# Ensure we import the real utils.logger module (in case previous tests stubbed utils)
if 'utils' in sys.modules and not hasattr(sys.modules['utils'], '__file__'):
    del sys.modules['utils']
for mod in ['utils.logger', 'utils.security']:
    if mod in sys.modules:
        del sys.modules[mod]
import utils.logger
importlib.reload(utils.logger)
from utils.logger import SecretsRedactionFilter


def test_secrets_redaction_filter_masks_secrets():
    filt = SecretsRedactionFilter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "Found key: sk-abcdef1234567890abcdef1234567890", (), None)
    allowed = filt.filter(record)
    assert allowed is True
    # Ensure sensitive payload is redacted (pattern replaced)
    assert "[SENSITIVE_DATA_REDACTED]" in str(record.getMessage())
    assert "abcdef1234567890abcdef1234567890" not in str(record.getMessage())
