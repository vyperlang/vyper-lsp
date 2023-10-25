# Vyper LSP Server

## Requirements

Vyper LSP requires a minimum vyper version of 0.3.7. For full support, it is also required that the Vyper version installed in your virtual environment is capable of compiling your contract.

For example, a vyper contract with `#pragma version 0.3.8` cannot be compiled with `0.3.10`, so you must install `vyper==0.3.8` if you want full support while working with this contract.

A contract with `#pragma version >=0.3.8` will work fine with any installed vyper version greater than the requirement, so you can get full support while editing this contract if you have the latest vyper version installed.

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

Coming Soon
