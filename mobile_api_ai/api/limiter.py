# -*- coding: utf-8 -*-
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=os.getenv('DEFAULT_RATE_LIMITS', '1000 per day, 300 per hour').split(', '),
    storage_uri=os.getenv('LIMITER_STORAGE_URI', 'memory://'),
)
