# Git Hooks do projeto

Hooks versionados, ativados apontando o git para esta pasta:

```bash
git config core.hooksPath .githooks
```

> O `core.hooksPath` é uma configuração **local** do clone. Após clonar o
> repositório, rode o comando acima uma vez para ativar os hooks.

## `commit-msg`

Bloqueia, em **qualquer** commit (independente de autor ou ferramenta):

- trailers `Co-Authored-By:` que mencionem **Claude** ou **Anthropic**;
- qualquer email **@anthropic.com**;
- menções de "Generated with ... Claude".

Garante que o histórico não registre co-autoria de IA.
