## Purpose

Record what an agent session spends on model calls in this repository, as it works, and carry it to the pull request with the agent's own commits, in a form the pull request's CI can read at merge without any external service.

## ADDED Requirements

### Requirement: Capture runs only where the tool is on and the person has opted in

The capture step SHALL record nothing unless the repository's configuration turns the tool on and the person running the session has turned capture on for themselves, in their global git configuration, which is not part of the repository. The step SHALL read that setting only from the global configuration files in the person's home directory themselves, not from files they include, ignoring any environment variable that points git at other configuration files or adds settings, and SHALL record nothing in a repository whose own git configuration turns capture off.

#### Scenario: No configuration file means no capture

- **WHEN** the capture step runs in a repository without the configuration file
- **THEN** nothing is recorded, and no ledger file is created

#### Scenario: A person who has not opted in is not recorded

- **WHEN** the repository turns the tool on, but the person running the session has not turned capture on
- **THEN** nothing is recorded, and no ledger file is created

#### Scenario: A repository's own git configuration cannot opt a person in

- **WHEN** only the repository's own git configuration turns capture on
- **THEN** nothing is recorded

#### Scenario: The environment cannot opt a person in

- **WHEN** the session's environment points git's global configuration at a file that turns capture on, or adds that setting through `GIT_CONFIG_COUNT` or `GIT_CONFIG_PARAMETERS`, and the person's own global configuration does not turn it on
- **THEN** nothing is recorded

#### Scenario: A setting in an included file does not opt a person in

- **WHEN** the person's global configuration includes another file, and only that file turns capture on
- **THEN** nothing is recorded

#### Scenario: A person can turn capture off in one repository

- **WHEN** the person has turned capture on in their global configuration, and the repository's own git configuration turns it off
- **THEN** nothing is recorded in that repository

### Requirement: Usage is recorded per model call

The capture step SHALL record each model call once. Each record SHALL hold the call's UTC day, its model, a SHA-256 hash of its message id, whether the main agent or a subagent made it, its input tokens, output tokens, cache-write tokens split by cache lifetime where the source gives it, and cache-read tokens, and, where the source gives them, the attributes that change its price: service tier, speed, inference region and server-side tool requests. A call SHALL be identified by its message id, so that a call the transcript writes over several lines, or that appears in more than one transcript, is recorded once. A call's usage SHALL be read from its lines that give a stop reason, because its earlier lines can give partial usage. A call none of whose lines gives a stop reason SHALL be read from its last line once the call is over: when a later call follows it in the same transcript, or when the agent that made it has stopped. The ledger SHALL count the calls read that way, because such lines give the usage of the call's start, with fewer output tokens and server-side tool requests than the call made. A call that is not over yet SHALL be left for a later run. A subagent's calls SHALL be read from the subagent's own transcript. To learn which calls the branch's ledger files already hold, the step SHALL read those files only as blobs from git, never through the working tree, skipping any path in the ledger folder that is not a regular file, and SHALL learn each file's size before reading it, skipping any file larger than the size bound that the ledger format documents.

#### Scenario: A turn's calls are recorded once

- **WHEN** a turn's transcript holds three model calls not yet recorded, and the agent then commits
- **THEN** the commit's new ledger file holds exactly three entries, one per call, with each call's model and token counts

#### Scenario: Running again records nothing twice

- **WHEN** the capture step runs a second time over the same transcript with no new calls
- **THEN** nothing new is recorded

#### Scenario: Switching branches records nothing twice

- **WHEN** the agent switches to another branch, and the capture step runs again over the same transcript
- **THEN** no call already recorded is recorded again

#### Scenario: A resumed session records nothing its branch already holds

- **WHEN** a session is resumed in a fresh clone of its branch, and the ledger files on that branch already hold some of its calls
- **THEN** none of those calls is recorded again

#### Scenario: Capture reads no ledger file through a link

- **WHEN** the branch holds a symbolic link in the ledger folder
- **THEN** capture reads nothing through it, and still records the session's calls

#### Scenario: Capture does not read an oversized ledger file

- **WHEN** the branch holds a ledger file larger than the size bound
- **THEN** capture does not read that file, and still records the session's calls

#### Scenario: A call written over several lines is recorded once

- **WHEN** one model call's message appears on three transcript lines, each giving its stop reason and the same usage
- **THEN** one entry is recorded for that call

#### Scenario: A call's partial lines are not used

- **WHEN** a call's first lines give partial usage and no stop reason, and its last line gives its stop reason and its final usage
- **THEN** its entry records the final usage

#### Scenario: A call followed by a later one is read without its stop reason

- **WHEN** none of a call's lines gives a stop reason, and a later call follows it in the same transcript
- **THEN** the call is recorded from its last line, and the ledger counts it as read without a stop reason

#### Scenario: A stopped agent's last call is read without its stop reason

- **WHEN** a subagent finishes, and none of the lines of its last call gives a stop reason
- **THEN** that call is recorded from its last line, and the ledger counts it as read without a stop reason

#### Scenario: A call still being written is recorded later

- **WHEN** none of a call's lines gives a stop reason, no later call follows it, and the agent that made it has not stopped
- **THEN** nothing is recorded for that call yet, and a later run records it

#### Scenario: Lines of one call that disagree are refused

- **WHEN** two transcript lines of one model call both give a stop reason, and give different usage
- **THEN** no entry is recorded for that call, and the ledger counts one refused call

#### Scenario: Subagent calls are included

- **WHEN** a session started a subagent whose calls are in its own transcript
- **THEN** the subagent's calls are recorded, marked as a subagent's

#### Scenario: Price attributes are recorded

- **WHEN** a call's usage gives its service tier, its speed, its inference region and a number of web searches, each a value the price table lists
- **THEN** its entry records each of them

#### Scenario: An entry records the UTC day, not the time

- **WHEN** a call's transcript time is `2026-03-02T01:30:00+02:00`
- **THEN** its entry's day is `2026-03-01`, and the entry holds no time of day

### Requirement: Only calls made from this repository are recorded

This repository SHALL be the one that holds the project directory that Claude Code gives the hook, whatever directory the hook runs in, and the registered command SHALL name the capture step's file through that project directory. The capture step SHALL record only the calls whose transcript line gives a working directory in this repository: a directory whose git common directory is this repository's, which includes this repository's worktrees and excludes another repository nested inside its folder. Calls whose line gives any other working directory, including another repository that the same session worked in, or a folder that contains this repository, SHALL NOT be recorded here.

#### Scenario: Calls made from outside this repository are not recorded

- **WHEN** a session made calls while its working directory was in another repository, or in a folder that contains this one
- **THEN** none of those calls is recorded in this one

#### Scenario: A repository nested inside this one is not this one

- **WHEN** a session made calls while its working directory was in a separate git repository inside this repository's folder
- **THEN** none of those calls is recorded in this one

#### Scenario: A worktree of this repository is this repository

- **WHEN** a session made calls while its working directory was in a worktree of this repository
- **THEN** those calls are recorded, and only a commit made in that worktree carries them

#### Scenario: A run from another directory works on this repository

- **WHEN** the capture step runs while Claude's current directory is in another repository
- **THEN** it records and stages only in this repository, and only the calls made from this repository

### Requirement: The ledger holds counts, never content

A ledger entry SHALL contain no prompt text, response text, code, file contents, tool name, tool input or output, file path, working directory, branch name, user name, session identifier or time of day. The only text an entry takes from the transcript SHALL be the model's name and the values of the price attributes, and each SHALL be recorded only when the price table that the capture step ships with lists it, so that the name of a private gateway, a custom model or an alias is not published. Any other value SHALL be recorded as `unknown`.

#### Scenario: Content in the transcript does not reach the ledger

- **WHEN** a transcript message carries text, a tool call with arguments and a session identifier
- **THEN** the entry recorded from it holds only the fields the usage requirement names and its activity type

#### Scenario: A planted string never reaches the ledger

- **WHEN** every text value in a transcript, other than model names and price attributes, is a distinct marker string
- **THEN** no marker appears anywhere in the ledger

#### Scenario: An unexpected model name is recorded as unknown

- **WHEN** a call's model name holds characters such as spaces, brackets or Markdown
- **THEN** its entry's model is `unknown`

#### Scenario: A model name the price table does not list is recorded as unknown

- **WHEN** a call's model name begins with `claude-` and is made only of lowercase letters, digits and hyphens, but the price table does not list it
- **THEN** its entry's model is `unknown`

#### Scenario: An attribute value the price table does not list is recorded as unknown

- **WHEN** a call's service tier is a value that the price table does not list
- **THEN** its entry's service tier is `unknown`

### Requirement: Counts are whole numbers

Every token count and request count SHALL be a whole number from zero up to a ceiling that the ledger format documents. A value that is text, a fraction, negative, not a number, `true` or `false`, or above the ceiling SHALL be refused: the call is left out, and the ledger counts it as refused, once, with nothing else about it.

#### Scenario: A count that is not a whole number is refused

- **WHEN** a call's output tokens are given as text, as a fraction, or as `true`
- **THEN** no entry is recorded for that call, and the ledger counts one refused call

#### Scenario: A negative count is refused

- **WHEN** a call's input tokens are negative
- **THEN** no entry is recorded for that call

### Requirement: Each entry carries an activity type

Each entry SHALL carry one activity type derived from the tools the model call invoked: code generation for file edits and writes, file reading for reads and searches, tooling for shell commands, MCP for MCP tool calls, subagent for starting a subagent, other for a tool the classification does not know, and conversation when no tool was called. A call that invoked tools of several types SHALL carry the type of its first tool call. A tool's name SHALL be read only to choose the type, and SHALL NOT be recorded.

#### Scenario: An edit is code generation

- **WHEN** a model call's only tool call edits a file
- **THEN** its entry's activity type is code generation

#### Scenario: An unknown tool is other

- **WHEN** a model call invokes a tool the classification does not know
- **THEN** its entry's activity type is other

#### Scenario: An MCP call does not record the server's name

- **WHEN** a model call invokes a tool of an MCP server
- **THEN** its entry's activity type is MCP, and no part of the tool's or the server's name is in the ledger

### Requirement: Usage reaches the pull request with the agent's commits

Capture SHALL run when Claude finishes responding, when a subagent finishes, when a turn ends in an API error, and before and after each of the agent's Bash commands that runs git. Every run SHALL record the calls that the transcript holds as over, so that a call that is over before a Bash command runs git is recorded with the branch it was made on, before that command can change the branch. A command runs `git commit` when one of the commands it is made of is `git`, with or without git's own options, followed by the `commit` subcommand, and is not a dry run; a command that only names it, such as in a quoted string, does not. Before a command that runs `git commit` in this repository in the foreground, in which nothing comes before that commit but changes of directory and the git commands `add`, `rm`, `mv`, `status`, `diff`, `log` and `show`, the step SHALL stage, as one new ledger file, the calls recorded in that worktree, while the branch now checked out there was checked out, that no ledger file holds yet. It SHALL add that file even when the repository's ignore rules match it. It SHALL stage nothing for any other command that runs `git commit`, because it cannot tell then which branch the commit lands on or when it runs; for a commit that names the paths to commit; and for a commit that would otherwise commit nothing when nothing before it in the command stages files, so that it fails, or makes the empty commit asked for, as it would without the tool. When the command's result returns, whether it succeeded or failed, the run for that command SHALL take the file back, from the index and the working tree, if no commit took it, and keep its calls for a later commit. When a command ends without that run, because it was refused, blocked by another hook or cancelled, the step's next run that finds the command over, by its result in the transcript or by its agent having stopped, SHALL take the file back the same way. A take-back SHALL NOT remove a file that a commit holds, and SHALL leave the file for a later run while another git command holds the index. At every other time, the step SHALL keep what it records inside the repository's common git directory, and SHALL NOT change the working tree or the index. Calls recorded while no branch was checked out SHALL go only to a commit made while no branch is checked out, in the same worktree.

#### Scenario: A one-turn session's commit carries its calls

- **WHEN** the agent makes model calls and then runs `git commit`, in the same turn
- **THEN** that commit adds a ledger file holding the calls recorded before it

#### Scenario: A turn's end leaves the working tree alone

- **WHEN** capture runs at the end of a turn in which the agent did not commit
- **THEN** the working tree and the index are unchanged, so switching branches or rebasing is not blocked

#### Scenario: A turn that ends in an API error is still recorded

- **WHEN** a turn ends in an API error
- **THEN** its calls are carried by the agent's next commit

#### Scenario: Calls go to the worktree and branch they were recorded on

- **WHEN** calls were recorded while one branch was checked out, and the agent then commits on another branch, or in another worktree
- **THEN** that commit carries none of those calls

#### Scenario: A call made before a checkout stays with its branch

- **WHEN** the agent makes calls with one branch checked out, then runs `git checkout` to another branch and commits there, in the same turn
- **THEN** the commit on the other branch carries none of the calls that the transcript held as over before the checkout ran

#### Scenario: Calls made with no branch checked out wait for a commit made the same way

- **WHEN** calls were recorded while no branch was checked out, and the agent then checks out a branch and commits
- **THEN** that commit carries none of those calls

#### Scenario: A commit that does not happen leaves nothing staged

- **WHEN** the step has staged a ledger file for a `git commit` that then fails
- **THEN** once that command has ended, the ledger file is neither staged nor in the working tree, and the agent's next commit on that branch carries its calls

#### Scenario: A refused commit leaves nothing staged

- **WHEN** the step has staged a ledger file for a `git commit` that is then refused at a permission prompt or by a permission rule, blocked by another hook, or cancelled, and the transcript then holds that command's result
- **THEN** after the step's next run, the ledger file is neither staged nor in the working tree, and a later commit on that branch carries its calls

#### Scenario: A take-back leaves a committed file in place

- **WHEN** a commit takes the ledger file after its command's result has returned, as a commit that Claude Code moved to the background at its timeout can
- **THEN** the file stays in that commit, and the step does not remove it from the index

#### Scenario: A commit that stages its own files carries a ledger file

- **WHEN** the agent runs `git add f && git commit -m x`, with nothing staged before
- **THEN** that commit holds `f` and a ledger file

#### Scenario: A commit after another command takes no ledger file

- **WHEN** the agent runs `npm test && git commit -am x`, or `git checkout other && git commit -m x`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit in the background takes no ledger file

- **WHEN** the agent runs `git commit` in the background
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit with nothing to commit stays empty

- **WHEN** the agent runs `git commit -m x` alone, with nothing staged
- **THEN** no ledger file is staged, and the command fails as it would have without the tool

#### Scenario: An empty commit asked for stays empty

- **WHEN** the agent runs `git commit --allow-empty -m x` alone, with nothing staged
- **THEN** no ledger file is staged, and the commit it makes is empty

#### Scenario: A commit of named paths takes no ledger file

- **WHEN** the agent runs `git commit` naming the paths to commit
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A command that only names a commit stages nothing

- **WHEN** the agent runs `git commit --dry-run`, or a command that only names `git commit` in its text, such as `grep 'git commit' notes.txt`
- **THEN** no ledger file is staged

#### Scenario: A commit with git's own options is still a commit

- **WHEN** the agent runs `git -c user.name=x commit -m y` in this repository
- **THEN** that commit carries a ledger file

#### Scenario: A commit in another repository stages nothing here

- **WHEN** the agent runs `git -C <another repository> commit`
- **THEN** no ledger file is staged in this repository

#### Scenario: An ignored ledger path is still committed

- **WHEN** the repository's ignore rules match the ledger files
- **THEN** the agent's commit still carries its ledger file

### Requirement: A ledger file is written once

Each ledger file SHALL be a new regular file with a random name, in the ledger folder for the UTC month in which it is written, and SHALL never be changed after it is written: a file that no commit took is removed whole, never edited. The capture step SHALL refuse to write when any folder on the ledger file's path below the repository root is a symbolic link, or when a file of that name already exists. It SHALL stage only the ledger file it wrote.

#### Scenario: A new file for every commit

- **WHEN** capture adds calls to a branch that already has ledger files
- **THEN** it writes a new file, and leaves every other ledger file unchanged

#### Scenario: A symbolic link in the ledger path is refused

- **WHEN** a folder on the ledger file's path below the repository root is a symbolic link
- **THEN** nothing is written through it

#### Scenario: Other changes stay unstaged

- **WHEN** the working tree holds other changed files and untracked files
- **THEN** the ledger file is the only change the step has staged

### Requirement: Runs at the same time keep every record whole

Two capture steps that run at the same time, such as a session's and a subagent's, or those of two worktrees of one repository, SHALL NOT split or interleave each other's records, and SHALL NOT both record the same call.

#### Scenario: Two runs at once

- **WHEN** two capture steps run over the same transcripts at the same moment
- **THEN** every record either kept is whole, and no call is recorded twice

#### Scenario: Two worktrees share one record of a call

- **WHEN** a session in this repository's main folder and a subagent in one of its worktrees both read the subagent's transcript
- **THEN** each of its calls is recorded once

### Requirement: The capture step is one self-contained file

The capture step SHALL be one Python file that imports nothing but Python's standard library, so that it runs in Python's isolated mode, which imports nothing from the file's own folder, and an adopter can copy it into their repository whole.

#### Scenario: The capture step runs alone in isolated mode

- **WHEN** the capture step's file is copied into a folder that holds nothing else but a planted `json.py`, and run with `python3 -I`
- **THEN** it runs, and the planted module is not imported

### Requirement: Capture never breaks or steers the session

A failure inside the capture step SHALL NOT stop or fail the agent's session. The registered command SHALL exit with success even when its script cannot be read or started. The step SHALL print nothing on standard output, SHALL write no text taken from the transcript or the ledger to standard error, and SHALL finish within a time budget, leaving what it has not read for a later run. On failure it SHALL leave the ledger and its own records as they were.

#### Scenario: An unreadable transcript is skipped

- **WHEN** the transcript path the hook receives does not exist
- **THEN** the step exits with success and records nothing

#### Scenario: Capture never asks the agent to continue

- **WHEN** the step fails for any reason, including when its script cannot be read or started
- **THEN** the registered command exits with success and has printed nothing on standard output

#### Scenario: A failure message quotes nothing from the transcript

- **WHEN** a transcript line that cannot be read contains text
- **THEN** the message on standard error contains none of that text

#### Scenario: A long transcript does not hold up the session

- **WHEN** reading the transcript would take longer than the time budget
- **THEN** the step stops at the budget and exits with success, and a later run records the rest
