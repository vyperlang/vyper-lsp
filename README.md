# Vyper LSP Server

## Requirements

Vyper LSP requires a minimum vyper version of 0.4.1. For full support, it is also required that the Vyper version installed in your virtual environment is capable of compiling your contract.

## Development

### Setting up Development Environment

1. **Install uv** (Fast Python package installer and resolver)

   ```bash
   # Install with pip
   pip install uv

   # Or on macOS with Homebrew
   brew install uv
   ```

2. **Clone the repository**

   ```bash
   git clone https://github.com/vyperlang/vyper-lsp.git
   cd vyper-lsp
   ```

3. **Install dependencies**

   ```bash
   uv pip install -e .
   ```

4. **Run tests**

   ```bash
   uv run pytest
   ```

### Code Quality and Testing

- Run linting: `ruff check .`
- Format code: `ruff format .`
- Generate test coverage: `coverage run -m pytest && coverage report`

## Install Vyper-LSP

### via `pipx`
I like `pipx` because it handles creating an isolated env for executables and putting them on your path.

`pipx install git+https://github.com/vyperlang/vyper-lsp.git`

### via `pip`
You can install using `pip` if you manage your environments through some other means:

`pip install git+https://github.com/vyperlang/vyper-lsp.git`

## Verify installation

Check that `vyper-lsp` is on your path:

In your terminal, run `which vyper-lsp`. If installation was succesful, you should see the path to your installed executable.

## Editor Setup

### Emacs

The following emacs lisp snippet will create a Vyper mode derived from Python Mode, and sets up vyper-lsp.

``` emacs-lisp
(define-derived-mode vyper-mode python-mode "Vyper" "Major mode for editing Vyper.")

(add-to-list 'auto-mode-alist '("\\.vy\\'" . vyper-mode))

(with-eval-after-load 'lsp-mode
  (add-to-list 'lsp-language-id-configuration
               '(vyper-mode . "vyper"))
  (lsp-register-client
   (make-lsp-client :new-connection
                    (lsp-stdio-connection `(,(executable-find "vyper-lsp")))
                    :activation-fn (lsp-activate-on "vyper")
                    :server-id 'vyper-lsp)))
```

### Neovim

Add the following to your `neovim` lua config.

It should be at `~/.config/nvim/init.lua`

``` lua
vim.api.nvim_create_autocmd({ "BufEnter" }, {
  pattern = { "*.vy" },
  callback = function()
    vim.lsp.start({
      name = "vyper-lsp",
      cmd = { "vyper-lsp" },
      root_dir = vim.fs.dirname(vim.fs.find({ ".git" }, { upward = true })[1])
    })
  end,
})

vim.api.nvim_create_autocmd({ "BufEnter" }, {
  pattern = { "*.vy" },
  callback = function()
    vim.lsp.start({
      name = "vyper-lsp",
      cmd = { "vyper-lsp" },
      root_dir = vim.fs.dirname(vim.fs.find({ ".git" }, { upward = true })[1])
    })
  end,
})

vim.api.nvim_set_keymap('n', 'gd', '<Cmd>lua vim.lsp.buf.definition()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'gD', '<Cmd>lua vim.lsp.buf.declaration()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'gr', '<Cmd>lua vim.lsp.buf.references()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'gi', '<Cmd>lua vim.lsp.buf.implementation()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', 'K', '<Cmd>lua vim.lsp.buf.hover()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<C-k>', '<Cmd>lua vim.lsp.buf.signature_help()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '[d', '<Cmd>lua vim.lsp.diagnostic.goto_prev()<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', ']d', '<Cmd>lua vim.lsp.diagnostic.goto_next()<CR>', { noremap = true, silent = true })

```


### VS Code

See `vyper-lsp` VS Code extension
