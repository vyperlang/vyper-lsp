# Vyper LSP Server

## Installation

## Install Vyper-LSP

### via `pipx` 
I like `pipx` because it handles creating an isolated env for executables and putting them on your path.

`pipx install git+https://github.com/vyperlang/vyper-lsp.git`

### via `pip`
You can install using `pip` if you manage your environments through some other means:

> TODO: publish on pypi

`pip install git+https://github.com/vyperlang/vyper-lsp.git`

## Verify installation

Check that `vyper-lsp` is on your path:

In your terminal, run `which vyper-lsp`. If installation was succesful, you should see the path to your installed executable.

## Editor Setup

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
```


### VS Code

Coming Soon

## Done

Opening any vyper file should result in the LSP server starting up and providing useful information
