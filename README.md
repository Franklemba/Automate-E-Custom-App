### Automatee Custom

Site customizations (DocTypes, fields, scripts) kept as code so they ship with git

### How customizations get into this app

Make customizations only on the development site, with `developer_mode` on.

| You create | Where it ends up |
|---|---|
| New DocType with Module = Automatee Custom | `automatee_custom/automatee_custom/doctype/` (the "Custom?" box is unticked for you) |
| Report, Print Format, Workspace etc. marked Standard, Module = Automatee Custom | `automatee_custom/automatee_custom/` |
| Custom Field / Property Setter (Customize Form or the Custom Field form) | `fixtures/custom_field.json`, `fixtures/property_setter.json` |
| Client Script / Server Script | `fixtures/client_script.json`, `fixtures/server_script.json` |

Records created in the desk with an empty Module are tagged Automatee Custom
automatically, and the fixture file is rewritten on every save. Records that other
apps create as a side effect are left alone. Deleted records are listed in
`deleted_records.json` and removed from other sites on `bench migrate`.

To export everything again by hand: `bench --site <site> export-fixtures --app automatee_custom`.

### Shipping to another site

```bash
cd apps/automatee_custom && git pull && cd ../..
bench --site <site> migrate
bench restart   # or restart `bench start` in development
```

First time on a site: `bench get-app <repo-url>` then `bench --site <site> install-app automatee_custom`.
Server Scripts only run where `server_script_enabled` is set (`bench set-config -g server_script_enabled 1`).

### Rules

- Never edit standard ERPNext/Frappe DocTypes directly. Use Customize Form.
- Keep `developer_mode` off in production. Fixtures overwrite the target site, so
  changes made directly on production are replaced on the next migrate.
- Fixtures are for configuration only, never transactional data.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app automatee_custom
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/automatee_custom
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
