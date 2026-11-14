# Optional extension API, version 1

An optional extension may import **only `utils.extensions`** from the core bot.
Check `API_VERSION == 1` before registering; incompatible versions fail clearly
instead of reaching into implementation modules. The module is safe to import
without Telegram/ORM initialization and does not depend on any private package.
Standalone core remains independently installable and deployable.

| Export | Contract |
|---|---|
| `API_VERSION` | Integer interface version; currently 1. |
| `SUPPORTED_LANGUAGES` | Ordered tuple of the core catalog languages. |
| `text(context, key, **values)` | Selected-language catalog lookup, fallback to English for unsupported language. |
| `language_or_fallback(user_data)` | Core's existing session-language fallback. |
| `feature_settings()` | Existing core feature-switch snapshot. |
| `disabled_message(language)` | Existing selected-language disabled-feature text. |
| `user_storage_root(user_id)` | Resolved `DATA_DIR/downloads/<positive Telegram ID>` root. Callers must still verify ownership/path containment for individual files. |
| `upsert_user(callback)` | Lazy core decorator; apply to registered commands and user-triggered callbacks. Background tasks are outside this requirement. |
| `register_keyboard_provider(name, provider)` | Register optional language/user-specific rows; same name replaces its provider. |
| `optional_keyboard_rows(...)` | Existing core keyboard aggregation; empty without installed extensions. |
| `show_module_selector(update, context)` | Async existing core selector behavior. |
| `start_over(update, context)` | Async existing core reset behavior. |
| `read_tags(update, user_data)` | Async core tag reader; same bool/result and supplied-state behavior as before. |
| `display_tag_preview(update, context)` | Async existing tag preview behavior. |

`register_optional_extension(application)` remains the operator-configured loader
for `BOT_EXTENSION=module:function`. It passes the core upsert decorator when the
extension registration signature supports it. Do not double-decorate nested
helpers or background jobs. Extensions must not import `modules.*`, `config.*`,
`database.*` or other `utils.*` implementations directly.

Version additions must remain backward compatible within v1. Breaking changes
require a new version and matching consumer updates. Implementation wrappers
remain owned by the free core, and private consumers test against a pinned core
revision. Tests verify lazy imports, delegation, language catalogs and upsert
behavior. Never copy private provider/payment/business code into core for this
interface.
