"""One current API configuration for luweixiao 4; no Stata or network calls.

configure(state, options) accepts the ado option names key, baseurl, model,
protocol, auth, allowhttp and timeout. keyfile/keyenv/effort remain backend
compatibility options. It returns the runtime configuration, including a key
resolved from keyenv when used. Never print that return value; public() is the
safe status interface. A direct key is deliberately saved in local config.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

import luweixiao_api as api


DEFAULTS = {
    'openai': ('https://discovery-api.intern-ai.org.cn/v1', 'glm-5.3'),
    'anthropic': ('https://api.anthropic.com', ''),
    'gemini': ('https://generativelanguage.googleapis.com/v1beta', ''),
}
_FIELDS = {'protocol', 'base_url', 'model', 'auth', 'api_key', 'key_env',
           'allowhttp', 'timeout', 'effort', 'max_output_tokens'}


def _present(options, name):
    """Empty ado locals mean that an option was omitted; False is explicit."""
    return name in options and options[name] is not None and options[name] != ''


def _stored(state):
    # A damaged current file must never silently reactivate legacy credentials.
    state = Path(state)
    path = next((state / name for name in ('config.json', 'config_default.json')
                 if (state / name).is_file()), None)
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, UnicodeError, ValueError):
        raise ValueError('无法读取当前 API 配置；请重新运行 luweixiao config。') from None
    if not isinstance(value, dict):
        raise ValueError('当前 API 配置不是有效对象；请重新运行 luweixiao config。')
    # Legacy aliases are read only; the new file always uses canonical names.
    for alias, canonical in (('key', 'api_key'), ('baseurl', 'base_url'), ('keyenv', 'key_env')):
        if canonical not in value and alias in value:
            value[canonical] = value[alias]
    return {key: value[key] for key in _FIELDS if key in value}


def _runtime(stored):
    config = dict(stored)
    if config.get('key_env'):
        config['api_key'] = os.environ.get(config['key_env'], '')
    try:
        timeout = config.get('timeout', 180)
        if isinstance(timeout, bool) or (isinstance(timeout, float) and not timeout.is_integer()):
            raise ValueError('timeout 必须为整数。')
        valid = api.validate_config(config)
        api.endpoint(valid)
    except (ValueError, TypeError) as error:
        message = api.redact(str(error), config)
        if str(error).startswith('尚未配置密钥'):
            message = '尚未设置可用密钥。运行 luweixiao config, key(你的密钥)；免密钥服务用 auth(none)。'
        raise ValueError(message) from None
    return valid


def load(state):
    """Load config.json first, otherwise legacy config_default.json; no writes."""
    config = _stored(state)
    return _runtime(config) if config else {}


def _flag(value):
    if isinstance(value, str) and value.strip().lower() == 'allowhttp':
        return True  # Stata represents a present no-argument option by its name.
    if isinstance(value, str):
        value = value.strip().lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        if value in ('false', '0', 'no', 'off', ''):
            return False
        raise ValueError('allowhttp 必须为 true 或 false。')
    return bool(value)


def _keyfile(path):
    try:
        return Path(path).read_text(encoding='utf-8-sig').strip()
    except (OSError, UnicodeError, TypeError):
        raise ValueError('无法读取 keyfile()；请确认文件存在且使用 UTF-8。') from None


def _save(state, config):
    """Atomic replacement prevents partial configuration files on write errors."""
    state = Path(state)
    temporary = None
    try:
        state.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         prefix='.config-', suffix='.tmp', dir=state,
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(temporary, state / 'config.json')
    except OSError:
        raise ValueError('无法保存 API 配置；请检查配置目录的写入权限。') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def configure(state, options):
    """Validate and save one current configuration; return its runtime copy.

    A protocol change clears the previous address, model and authentication.
    A model change clears inherited effort unless explicitly supplied again.
    Only the initial glm-5.3 configuration defaults to low effort. Supplying a
    new key defaults to authenticated access unless auth(none) is explicit.
    """
    options = dict(options or {})
    try:
        old = _stored(state)
    except ValueError:
        # An explicit configuration action may repair a malformed file. It still
        # needs a fresh usable key/auth and complete provider settings to save.
        old = {}
    old_protocol = str(old.get('protocol') or 'openai').strip().lower()
    protocol = str(options.get('protocol') or old_protocol).strip().lower()
    if protocol not in DEFAULTS:
        raise ValueError('protocol() 请选择 openai、anthropic 或 gemini。')
    changed_protocol = bool(old) and protocol != old_protocol
    config = {} if changed_protocol else dict(old)
    base, default_model = DEFAULTS[protocol]
    config.update(protocol=protocol, base_url=config.get('base_url') or base,
                  model=config.get('model') or default_model,
                  auth=config.get('auth') or 'bearer', timeout=config.get('timeout', 180),
                  allowhttp=config.get('allowhttp', False))
    for option, field in (('baseurl', 'base_url'), ('base_url', 'base_url'),
                          ('model', 'model'), ('auth', 'auth'), ('timeout', 'timeout')):
        if _present(options, option):
            config[field] = options[option]
    if _present(options, 'allowhttp'):
        config['allowhttp'] = _flag(options['allowhttp'])
    credentials = [name for name in ('key', 'keyfile', 'keyenv') if _present(options, name)]
    if len(credentials) > 1:
        raise ValueError('key()、keyfile()、keyenv() 请选择一种。')
    if credentials:
        config.pop('api_key', None)
        config.pop('key_env', None)
        name = credentials[0]
        if name == 'keyenv':
            env_name = str(options[name]).strip()
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', env_name):
                raise ValueError('keyenv() 需要有效的环境变量名。')
            config['key_env'] = env_name
        else:
            config['api_key'] = _keyfile(options[name]) if name == 'keyfile' else str(options[name]).strip()
        if not _present(options, 'auth'):
            config['auth'] = 'bearer'
    config['auth'] = str(config['auth']).strip().lower()
    if config['auth'] == 'none':
        config.pop('api_key', None)
        config.pop('key_env', None)
    new_model = str(config['model']).strip()
    changed_model = bool(old) and new_model != str(old.get('model') or '').strip()
    if _present(options, 'effort'):
        config['effort'] = options['effort']
    elif changed_protocol or changed_model:
        config['effort'] = 'default'
    elif not config.get('effort'):
        config['effort'] = 'low' if protocol == 'openai' and new_model.lower() == 'glm-5.3' else 'default'
    runtime = _runtime(config)
    saved = {key: runtime[key] for key in _FIELDS if key in runtime}
    if config.get('key_env'):
        saved['key_env'] = config['key_env']
        saved.pop('api_key', None)
    elif saved.get('auth') == 'none':
        saved.pop('api_key', None)
        saved.pop('key_env', None)
    _save(state, saved)
    return runtime


def public(config):
    """Return status fields only; redact secrets even in accidental metadata."""
    config = dict(config or {})
    secret = dict(config)
    if config.get('key_env'):
        secret['api_key'] = os.environ.get(config['key_env'], '')
    status = lambda name, default='': api.redact(str(config.get(name) or default), secret)
    none = config.get('auth') == 'none'
    key_set = bool(secret.get('api_key')) and not none
    timeout = config.get('timeout', 180)
    if not isinstance(timeout, int) or isinstance(timeout, bool):
        timeout = 180
    return {'configured': bool(config), 'protocol': status('protocol'),
            'base_url': status('base_url'), 'model': status('model'),
            'auth': 'none' if none else 'bearer', 'key_configured': key_set,
            'key_status': '免密钥' if none else ('已设置' if key_set else '未设置'),
            'timeout': timeout, 'allowhttp': bool(config.get('allowhttp', False)),
            'effort': status('effort', 'default')}
