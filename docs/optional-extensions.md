# Optional bot extension

The bot supports an operator-installed extension through `BOT_EXTENSION`.
With that variable absent or empty, no extension is imported and the bot keeps
its ordinary dependencies and behavior.

The value is a trusted local Python callable in `module:function` form:

```text
BOT_EXTENSION=example_extension:register
```

Install the extension separately into the existing bot's Python environment.
Its `register(application)` function receives the Telegram Application and can
add its handlers. Registration happens before the core catch-all handlers.
The extension must not start another polling process or run long remote jobs
inside the bot's sequential update handlers.

An explicitly configured missing or invalid extension causes startup to fail,
so the operator can correct the configuration. No extension code, commercial
credentials or business configuration is bundled in this public repository.
Leave `BOT_EXTENSION` unset for standalone deployment.

Validate the dependency-free loader with:

```sh
python3 -m unittest discover -s tests/extensions -v
```
