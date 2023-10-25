# Vyper LSP Architecture

LSP stands for Language Server Protocol. It enables us to provide IDE-like features in an editor-agnostic way. LSP defines certain methods that a client and server can expect to use to communicate with each other, such that the server can be language-specific and the client can be editor-specific, and the user gets the best of both.

Pygls is a very intuitive framework for building an LSP server. It follows an approach similar to FastAPI, letting us define and assign handlers for each "method" the LSP server should speak.

We have separated concerns across a few different layers in order to best allow the LSP server to grow and extend over time.

## Server Layer

This is currently confined to `vyper_lsp/main.py`

In this layer, we want to define handlers for each LSP method, and in those handlers invoke the appropriate module to compute a valid response.

This means this layer should have minimal logic of its own. There should be no concept of ASTs, any source-code level features, syntax, etc. at this layer. Only what is required to start up the server itself, and hook up LSP methods to the appropriate sources of data.

## Analyzer Layer

This is currently made up of the modules under `vyper_lsp/analyzers/`. Here, we define a base class called `BaseAnalyzer` which defines the interface our server layer will use to communicate with the Analyzer layer.

Currently there are two "analysis" functions we support

- `hover_info`: returns information about a symbol being hovered over
- `get_diagnostics`: returns a list of errors or warnings to be reported to the user
- `get_completions`: returns a list of suggested completions for the current cursor position

Analyzers classes expose functions which act on `Document` and `Params` arguments. `Document` represents the file being worked on. Through the `Document` class, `Analyzers` can easily access the entire source of the contract, as well as line-by-line information, filename, etc. `Params` will be specific to each method, and contain necessary information to answer queries for that method. For example, the params object when looking up information about a given symbol will include the current cursor position, which in combination with the line-by-line source code exposed by the `Document`, can be used to determine what symbol we're looking up.

It is up to Analyzers to determine how they will return appropriate results given a query. They should abstract this away from the Server layer entirely.

The two currently implemented `Analyzers` are the `ASTAnalyzer` and the `SourceAnalyzer`.

### ASTAnalyzer

This is where the most rich processing can happen, but where our tightest requirements around Vyper versions are.

This analyzer attempts to compile the current contract via Vyper as a library. This means the version of Vyper we have installed must

- Be capable of compiling this contract according to version requirements
- Be >= 0.3.7 so we can use the internal APIs our analysis depends on

This Analyzer is a good example of abstracting things away from the Server layer. It operates primarily on ASTs and nodes within it, but should not expose any implementation details about this to the Server layer.

### SourceAnalyzer

This analyzer should not be used unless the Vyper version of the contract being worked with is too old to run AST analysis on.

This is a sort of "fallback" analyzer. This does not depend on Vyper as a library, in hopes of loosening Vyper version requirements. It does two stages of analysis.

#### Syntax Analysis

This leverages Vyper's `lark` grammar to check for syntax errors. This does not catch semantic errors. For example, with syntax analysis we can tell that `x + foo(7) = 24;` is wrong for many reasons (not valid syntax), but we can't tell that `x: uint256 = "hello"` is wrong (not valid semantics)

#### Semantic Analysis

This analyzer also tries to do some semantic analysis. It leverages `vvm` to compile contracts with version requirements incompatible with currently installed Vyper, and reports any errors encountered.

This lets us work with a wider array of Vyper versions, but is significantly slower to use, due to overhead involved in going through the shell. There is also a big limit on what information we can gain other than compilation errors, because for successful compilation, we're limited to the cli outputs as defined in that Vyper version.


## Navigation Layer

This layer is made up of modules which expose classes that can handle navigation-related lookups. This is stuff like "find the declaration of this symbol". We currently have an AST navigator implemented in `vyper_lsp/navigation.py`

There is potential to implement navigation support that does not require AST analysis by leveraging the Lark grammar to parse into an unchecked Lark AST. This will be lacking any Vyper information such as type, etc. but is nicer to work with than raw source.
