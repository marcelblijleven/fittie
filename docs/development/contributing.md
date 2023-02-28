# Contributing

## Committing

Commits should follow the [conventional commit specification](https://www.conventionalcommits.org/en/v1.0.0/).
This makes automatic versioning and generating the changelog possible.

### Commitizen

[Commitizen](https://github.com/commitizen-tools/commitizen) is part of the dev requirements, it is a cli tool to generate conventional commits,
automatic changelogs and version tags.

If you need help creating a conventional commit, just run `cz commit` and the cli tool
will guide you through it.

When you're ready to create a new version, run `cz bump`. This will automatically create 
the changelog and bump the version based on the commit messages since the last version.
