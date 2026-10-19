## Purpose

Record what an agent session spends on model calls in this repository, as it works, and carry it to the pull request with the agent's own commits, in a form the pull request's CI can read at merge without any external service.

In the scenarios below, a commit that is expected to carry a ledger file is made where git's attributes give the ledger path no filter and no working-tree encoding, git does not refuse to add the file, and no git hook of the repository refuses it, and a commit that a scenario does not spell out, such as the agent's next commit, is one that the step stages for, unless the scenario says otherwise. In them, each run of the step reads the transcripts to their end within its time budget, unless the scenario says otherwise.

## ADDED Requirements

### Requirement: Capture runs only where the tool is on and the person has opted in

The capture step SHALL record nothing unless the repository's configuration turns the tool on and the person running the session has turned capture on for themselves, in their global git configuration, which is not part of the repository. The step SHALL read that setting only from the person's global configuration files themselves, `~/.gitconfig` and git's configuration file in their XDG configuration folder, which is `$XDG_CONFIG_HOME/git/config` when that variable holds an absolute path and `~/.config/git/config` otherwise, not from files they include, ignoring any environment variable that points git at other configuration files or adds settings. Where both files set it, `~/.gitconfig`, which git reads after the other, SHALL decide. The step SHALL record nothing in a repository whose own git configuration turns capture off.

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

- **WHEN** the person's global configuration includes a file that is not one of their global configuration files, and only that included file turns capture on
- **THEN** nothing is recorded

#### Scenario: The XDG configuration file can opt a person in

- **WHEN** the repository turns the tool on and its own git configuration does not set capture, the person's `~/.gitconfig` exists and does not set capture, and git's configuration file in their XDG configuration folder turns it on
- **THEN** the session's calls are recorded

#### Scenario: The home configuration file decides when both set it

- **WHEN** git's configuration file in the person's XDG configuration folder turns capture on, and their `~/.gitconfig` turns it off
- **THEN** nothing is recorded

#### Scenario: A relative XDG folder is not read

- **WHEN** `XDG_CONFIG_HOME` holds a relative path, and only a git configuration file at that path inside the repository turns capture on
- **THEN** nothing is recorded

#### Scenario: A person can turn capture off in one repository

- **WHEN** the person has turned capture on in their global configuration, and the repository's own git configuration turns it off
- **THEN** nothing is recorded in that repository

### Requirement: Usage is recorded per model call

The capture step SHALL record each model call once. Each record SHALL hold the call's UTC day, its model, a SHA-256 hash of its message id, whether the main agent or a subagent made it, its input tokens, output tokens, cache-write tokens split by cache lifetime where the source gives it, and cache-read tokens, and, where the source gives them, the attributes that change its price: service tier, speed, inference region and server-side tool requests. A call SHALL be identified by its message id, so that a call the transcript writes over several lines, or that appears in more than one transcript, is recorded once. A call's usage SHALL be read from its lines that give a stop reason, because its earlier lines can give partial usage. A call none of whose lines gives a stop reason SHALL be read from its last line once the call is over: when a later call follows it in the same transcript, or when the agent that made it has stopped. The ledger SHALL count the calls read that way, because such lines give the usage of the call's start, with fewer output tokens and server-side tool requests than the call made. A call that is not over yet SHALL be left for a later run. A subagent's calls SHALL be read from the subagent's own transcript. To learn which calls the branch's ledger files already hold, the step SHALL read those files only as blobs from git, never through the working tree, skipping any path in the ledger folder that is not a regular file, and SHALL learn each file's size before reading it, skipping any file larger than the size bound that the ledger format documents.

#### Scenario: A turn's calls are recorded once

- **WHEN** a turn's transcript holds three model calls not yet recorded, which the agent made in one worktree, and the agent then commits in that worktree, with no change of branch there in between and no other call waiting to be staged there
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

- **WHEN** a session made calls while its working directory was in a worktree of this repository, whether inside the repository's own folder, as Claude Code's worktrees are, or outside it, and no ledger file that the step wrote was in a stash
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

Capture SHALL run when Claude finishes responding, when a subagent finishes, when a turn ends in an API error, when the session ends, and before and after each of the agent's Bash commands that the hook's condition `Bash(git *)` matches. Every run SHALL record the calls that the transcript holds as over, up to its time budget, so that a call that the transcript holds as over when the run before such a command reads it is recorded before that command can change the branch, unless that run reaches its time budget before it reads that call. A call SHALL go only into a ledger file staged in the worktree that git itself finds from its line's working directory, which for a directory in a worktree inside the repository's folder is that worktree and not the main checkout around it, for a commit on the branch that was checked out there when the call was recorded. Calls recorded while no branch was checked out SHALL go only to a commit made while no branch is checked out, in the same worktree. Apart from staging a ledger file, taking it back and putting it back, as the next two requirements say, the step SHALL keep what it records inside the repository's common git directory, and SHALL NOT change the working tree or the index.

#### Scenario: A one-turn session's commit carries its calls

- **WHEN** in a session's first turn, the agent makes model calls in one worktree and then makes its first commit there, by running `git commit -m x` alone with changes staged, with no change of branch there in between, and the transcript holds at least one of those calls as over when that commit's run reads it
- **THEN** that commit adds a ledger file holding each of those calls that the transcript held as over by then

#### Scenario: A turn's end leaves the working tree alone

- **WHEN** capture runs at the end of a turn in which the agent did not commit, and no ledger file is due to be taken back or put back
- **THEN** the working tree and the index are unchanged, so switching branches or rebasing is not blocked

#### Scenario: A turn that ends in an API error is still recorded

- **WHEN** a turn in which the agent makes model calls in one worktree and does not commit ends in an API error, and the agent's next commit is made in that worktree, with no change of branch there from the start of that turn until that commit
- **THEN** once the run of the step when that turn ends is over, each of those calls that the transcript held as over when that run read it is recorded, and that commit carries them

#### Scenario: Calls go to the worktree and branch they were recorded on

- **WHEN** calls were recorded in a worktree while one branch was checked out there, and the agent then commits in another worktree, or in that worktree on another branch, and until that commit no stash held any of those calls, and no file held any of them in the index or the working tree of the worktree where the agent commits but the ledger files of the commit checked out there
- **THEN** that commit carries none of those calls

#### Scenario: A call made before a checkout stays with its branch

- **WHEN** the agent makes calls with one branch checked out, then, with no change of branch in between, runs `git checkout` to another branch and commits on that branch, in the same turn, and until that commit no stash holds any of those calls, and no file holds any of them in the index or the working tree but the ledger files of the commit checked out there
- **THEN** the commit on the other branch carries none of those calls that the transcript held as over when the last run of the step before the checkout read it

#### Scenario: Calls made with no branch checked out wait for a commit made the same way

- **WHEN** calls were recorded while no branch was checked out, and the agent then checks out a branch and commits
- **THEN** that commit carries none of those calls

### Requirement: A ledger file is staged only for a commit whose branch and contents the step can tell

A command runs `git commit` when one of the commands it is made of is `git`, with or without git's own options, followed by the `commit` subcommand, and is not a dry run, which it is when any of `--dry-run`, `--short`, `--porcelain`, `--long`, `-z` and `--null`, in any spelling that git accepts, abbreviated or combined with other short options, is in effect once git has read all of the commit's options, where `--short`, `--porcelain` and `--long` are one setting, which the `--no-` form of any of them clears; a command that only names it, such as in single quotes or as an argument of another command, does not. Before a command that runs `git commit` in this repository, the step SHALL stage, as one new ledger file, the calls recorded in the worktree where the commit runs, while the branch now checked out there was checked out, that no ledger file on that branch holds and that the step has not noted as taken, as the next requirement says, when the commit is one of the command's top-level commands, not part of a pipeline, joined to the others by `&&`, `;` or line breaks, runs in the foreground, and comes after nothing but `cd` to a path that the command writes out and the git commands `add`, `rm`, `mv`, `status`, `diff`, `log` and `show`, with or without git's own options. Each command substitution and process substitution in the commit or in a command before it, whether in an argument, a leading assignment or a redirection, SHALL count as a command that comes before the commit, unless all it runs is `cat` reading a here-document whose delimiter is quoted, in whole or in part, so that the shell expands nothing in its body. The step SHALL stage nothing when the commit or a command before it reads a here-document whose delimiter is not quoted, because the shell then runs any command substitution in its body. A run that comes again before the same command, as when a call that another hook deferred is resumed, SHALL stage nothing new while the file it staged for that command is still staged and the branch that it was staged for is still checked out there, and when that branch is no longer checked out there, SHALL first take that file back, as the next requirement says. The step SHALL find the worktree where the commit runs from the current directory that the hook's input gives, followed through each top-level `cd` before the commit and through the `-C` options that the commit's own git command is given before `commit`, and never from the directory that the hook runs in, and SHALL stage nothing when such a `-C` option names a path that the command does not write out. It SHALL add the file even when the repository's ignore rules match it, or a sparse checkout leaves its folder out, and when git refuses to add it, the step SHALL remove the file it wrote and stage nothing. It SHALL stage nothing for any other command that runs `git commit`, such as one in a pipeline, run in the background or followed by `&`, because it cannot tell then which branch the commit lands on or when it runs; for a commit that names the paths to commit; for a commit that would otherwise commit nothing, counting the changes to tracked files that `-a` adds, when no `git add`, `git rm` or `git mv` comes before it, so that it fails, or makes the empty commit asked for, as it would without the tool; when a `git rm` or `git mv` before the commit is given a `-C` option that names a path that the command does not write out, or names a path with a wildcard or other pathspec magic, a path that the command does not write out, or the folder that the ledger file is written in or a folder above it, with its paths read from the directory where it runs, after the `cd`s before it and its own `-C` options, because `git rm` then refuses to remove the newly staged file and fails the command, and `git mv` moves it where the step does not look for it; when there is no such call to stage; and when git's attributes for the ledger path, from whichever file git reads them, include a filter or a working-tree encoding, because the commit could then hold something other than the entries as they were written.

#### Scenario: A commit that stages its own files carries a ledger file

- **WHEN** the agent runs `git add f && git commit -m x`, with nothing staged before, and calls are waiting to be staged
- **THEN** that commit holds `f` and a ledger file

#### Scenario: A `git add` that stages nothing leaves the ledger file alone in the commit

- **WHEN** the agent runs `git add f && git commit -m x`, where `f` has no changes, with nothing staged before, and calls are waiting to be staged
- **THEN** the commit is made, and holds a ledger file and nothing else

#### Scenario: A commit message from a here-document still carries a ledger file

- **WHEN** the agent runs `git commit -m "$(cat <<'EOF'`, then the lines of the message, then `EOF` and `)"`, whose here-document's delimiter is quoted, with changes staged and calls waiting to be staged
- **THEN** that commit carries a ledger file

#### Scenario: A commit whose message another command writes takes no ledger file

- **WHEN** the agent runs `git commit -m "$(./message.sh)"` or `git commit -F <(./message.sh)`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A substitution before the commit takes no ledger file

- **WHEN** the agent runs `git add "$(./pick.sh)" && git commit -m x`, or `X="$(./prepare.sh)" git commit -m x`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A here-document whose delimiter is not quoted takes no ledger file

- **WHEN** the agent passes a commit message in a here-document whose delimiter is not quoted, as in `git commit -F - <<EOF` or `git commit -m "$(cat <<EOF`, followed by the lines of the message and `EOF`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit after another command takes no ledger file

- **WHEN** the agent runs `npm test && git commit -am x`, or `git checkout other && git commit -m x`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit in the background takes no ledger file

- **WHEN** the agent runs `git commit` in the background, or as `git commit -m x &`
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit with nothing to commit stays empty

- **WHEN** the agent runs `git commit -m x` alone, with nothing staged
- **THEN** no ledger file is staged, and the command fails as it would have without the tool

#### Scenario: An empty commit asked for stays empty

- **WHEN** the agent runs `git commit --allow-empty -m x` alone, with nothing staged
- **THEN** no ledger file is staged, and the commit it makes is empty

#### Scenario: A commit of all changes with nothing staged carries a ledger file

- **WHEN** the agent runs `git commit -am x` alone, with nothing staged, a tracked file changed and calls waiting to be staged
- **THEN** that commit holds the changed file and a ledger file

#### Scenario: A commit with nothing new to record takes no ledger file

- **WHEN** the agent commits, and a ledger file already holds every call recorded in that worktree on that branch
- **THEN** no ledger file is staged

#### Scenario: A commit of named paths takes no ledger file

- **WHEN** the agent runs `git commit` naming the paths to commit
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: Removing the ledger folder before a commit takes no ledger file

- **WHEN** the agent runs `git rm -r .pr-cost && git commit -m x`, `git -C .pr-cost rm -r ledger && git commit -m x`, or `git -C "$P" rm -r ledger && git commit -m x`, where that variable holds `.pr-cost`, on a branch that holds ledger files, with calls waiting to be staged
- **THEN** no ledger file is staged, and the command removes the folder and commits, as it would without the tool

#### Scenario: Moving the ledger folder before a commit takes no ledger file

- **WHEN** the agent runs `git mv .pr-cost old && git commit -m x`, `git -C .pr-cost mv ledger ../old && git commit -m x`, or `git -C "$P" mv ledger ../old && git commit -m x`, where that variable holds `.pr-cost`, on a branch that holds ledger files, with calls waiting to be staged
- **THEN** no ledger file is staged, and the command moves the folder and commits, as it would without the tool

#### Scenario: Removing ledger files by a pattern before a commit takes no ledger file

- **WHEN** the agent runs `git rm '*.jsonl' && git commit -m x` or `git rm -r ':(icase).PR-COST' && git commit -m x` on a branch that holds ledger files, with calls waiting to be staged
- **THEN** no ledger file is staged, and the command removes those files and commits, as it would without the tool

#### Scenario: A command that only names a commit stages nothing

- **WHEN** the agent runs `git commit --dry-run`, `git commit --dry`, `git commit --porcelain` or `git commit -z`, or a command that only names `git commit` in its text, such as `grep 'git commit' notes.txt`
- **THEN** no ledger file is staged

#### Scenario: A dry-run option that a later option undoes is still a commit

- **WHEN** the agent runs `git commit --dry-run --no-dry-run -m x`, `git commit -z --no-null -m x` or `git commit --porcelain --no-short -m x` alone, with changes staged and calls waiting to be staged
- **THEN** that commit carries a ledger file

#### Scenario: A commit with git's own options is still a commit

- **WHEN** the agent runs `git -c user.name=x commit -m y` in this repository
- **THEN** that commit carries a ledger file

#### Scenario: A `-C` after `commit` is not a path

- **WHEN** the agent runs `git commit -C HEAD` alone, on a branch that has a commit, with changes staged and calls waiting to be staged
- **THEN** that commit carries a ledger file

#### Scenario: A commit in another repository stages nothing here

- **WHEN** the agent runs `git -C <another repository> commit`
- **THEN** no ledger file is staged in this repository

#### Scenario: A commit whose `-C` path is not written out takes no ledger file

- **WHEN** the agent runs `git -C "$WT" commit -m x`, where that variable holds the path of one of the repository's worktrees, with calls waiting to be staged there
- **THEN** no ledger file is staged, and the calls wait for a later commit

#### Scenario: A commit stages in the worktree where it runs

- **WHEN** calls were recorded in one of the repository's worktrees, with the branch now checked out there, and the agent commits there, while the hook runs in the repository's main folder, or after a `cd` to that worktree's path, or with a `-C` before `commit` that names it, written out in the same command
- **THEN** the ledger file is staged in that worktree, holding those calls, and the main folder's index is unchanged

#### Scenario: A command's repeated run stages its calls once

- **WHEN** the run before a `git commit` fires a second time for the same call, as when a call that another hook deferred is resumed, with the same branch checked out, and no commit has taken the file staged the first time
- **THEN** that commit carries one ledger file of those calls: the one staged the first time if it is still staged, or else a new one

#### Scenario: A command's repeated run after a change of branch takes its file back

- **WHEN** the run before a `git commit` fires a second time for the same call, as when a call that another hook deferred is resumed, after the person checked out another branch while the file staged the first time was still staged, no commit has taken that file since, and no other git command holds the index
- **THEN** that run takes the file back before the commit runs, and the commit carries none of the calls recorded on the first branch

#### Scenario: An ignored ledger path is still committed

- **WHEN** the repository's ignore rules match the ledger files
- **THEN** the agent's commit still carries its ledger file

#### Scenario: A sparse checkout still commits the ledger file

- **WHEN** the agent commits in a sparse checkout that leaves out the ledger folder
- **THEN** that commit still carries its ledger file

#### Scenario: A ledger path with a filter takes no ledger file

- **WHEN** git's attributes for the ledger path give it a filter, such as Git LFS, or a working-tree encoding, whether the repository's `.gitattributes`, its `.git/info/attributes` or the person's own attributes file sets it
- **THEN** no ledger file is staged, and none is written in the working tree

#### Scenario: A ledger file that git refuses to add is not left behind

- **WHEN** git refuses to add the ledger file, as it does where `core.safecrlf` is on and line endings are converted
- **THEN** no ledger file is staged, none is left in the working tree, and the calls wait for a later commit

### Requirement: A ledger file that no commit takes is taken back

A commit holds a ledger file in a worktree when the commit checked out there holds it. When the result of the command that the file was staged for returns, whether the command succeeded or failed, the run after that command SHALL take the file back, from the index and the working tree of the worktree where it was staged, unless a commit holds it there, and its calls SHALL wait for a later commit. A command that gets no such run, because it was refused, blocked by another hook, cancelled or interrupted, SHALL have its file taken back the same way by any later run of the step in the repository, in that session or another, that finds the command over: by its result in a transcript, by a later call of the agent that ran it, by that agent having stopped, or by its session having ended. A take-back SHALL NOT remove a file from a worktree where a commit holds it, and SHALL leave the file for a later run while another git command holds that worktree's index. Once a run finds a commit holding a ledger file that the step staged, the step SHALL note the file's calls as taken in that run's clone, and SHALL never stage them again there, whatever later removes the file from the branch, the index or the working tree, so that a ledger file that anyone removes once a run has found a commit holding it takes its calls with it, even when the changes of that commit are committed again. The step SHALL take back only a file that it staged and that no run has found a commit holding, and SHALL leave any other ledger file to git, wherever git leaves it, as a mixed `git reset`, with or without `-N`, or a `git rm --cached` and a commit leave it in the working tree, so that a later commit that takes it again, as a squash made with a mixed `git reset` and `git add -A` does where no ignore rule matches the ledger path and no sparse checkout leaves it out, carries its calls, with the other changes that the reset leaves. A commit can still take a file that a take-back removes, as a commit that is still running can while the step takes the file back, and a later `git reset` can go back to a commit that took the file, as after a reset in that commit's own command. So the step SHALL note, for each file that it takes back, the commit that it found checked out there, not holding the file, and whether it removed the file from the index, the working tree or both. The first later run there that finds another commit checked out and the index free SHALL put the file back where the take-back removed it, as that commit holds it, when that commit holds it: into the index, when the take-back removed it from there and the index lacks it, and then into the working tree, when the take-back removed it from there, the index holds it as that commit does and the working tree lacks it. That run SHALL then forget the note, whether it put the file back or not. The step SHALL put back no file in any other case. A fresh clone at the same path holds no note, so a session resumed there can stage again the calls of a file that its branch no longer holds.

#### Scenario: A commit that does not happen leaves nothing staged

- **WHEN** the step has staged a ledger file for a `git commit` that then fails
- **THEN** once that command has ended, the ledger file is neither staged nor in the working tree, and the agent's next commit on that branch, in the worktree where the file was staged, carries its calls

#### Scenario: A refused commit leaves nothing staged

- **WHEN** the step has staged a ledger file for a `git commit` that is then refused at a permission prompt or by a permission rule, blocked by another hook, or cancelled, the transcript then holds that command's result, no commit has taken the file, and no other git command holds the index at the step's next run
- **THEN** after that run, the ledger file is neither staged nor in the working tree, and a later commit on that branch, in the worktree where the file was staged, carries its calls

#### Scenario: A session's end takes back what its commands left staged

- **WHEN** a session ends while the step has a ledger file staged for one of its commands that no commit took, such as a `git commit` that was interrupted, no other git command holds the index of its worktree, and the session's transcript holds more than that run can read within its time budget
- **THEN** the run when the session ends takes the file back, from the index and the working tree

#### Scenario: A later session takes back what an earlier one left staged

- **WHEN** a session was interrupted while the step had a ledger file staged for its `git commit`, no commit took the file, no later run of that session took it back, as when its process was then killed, and another session's run in the repository finds that command's result in the earlier session's transcript while no other git command holds the index
- **THEN** that run takes the file back, from the index and the working tree

#### Scenario: A take-back waits while the index is in use

- **WHEN** a ledger file is due to be taken back, and another git command that does not commit the file holds the index lock of its worktree
- **THEN** the run leaves the file and the lock as they are, and a later run takes the file back

#### Scenario: A take-back leaves a committed file in place

- **WHEN** a commit takes the ledger file after its command's result has returned, as a commit that Claude Code moved to the background at its timeout can, whether before a take-back of that file runs or while it runs, and before the step next runs there with that commit checked out and the index free, nothing but a take-back removes the file from the index or the working tree, and no other commit is made in that worktree
- **THEN** the file stays in that commit, and after that run the index and the working tree hold it as that commit does

#### Scenario: A file that a later commit deleted is not put back

- **WHEN** a take-back removes a ledger file while a commit that takes it is still running, the person then makes another commit on that branch in that worktree that does not hold the file, before any run of the step finds the first commit checked out there, and that other commit stays checked out there until the agent's next commit
- **THEN** no run of the step puts the file back, and the agent's next commit on that branch carries its calls

#### Scenario: A file removed from the index while its commit runs stays removed

- **WHEN** a commit that takes the ledger file is still running after its command's result has returned, another command removes the file from the index with `git rm --cached`, a take-back of the file then finds it only in the working tree, and the step next runs there with that commit checked out and the index free
- **THEN** after that run, neither the index nor the working tree holds the file, and the next commit there does not hold it

#### Scenario: A ledger file that a person removes stays removed

- **WHEN** a run of the step has found the commit checked out in a worktree holding a ledger file that the step staged, while no other git command held that worktree's index, and the person then removes that file there with `git rm`, with or without `--cached`, or with `git reset`, mixed or `--hard`, to a commit before the one that holds it, and the session goes on in that run's clone
- **THEN** no run of the step puts the file back there, and no ledger file that the step stages there later holds its calls

#### Scenario: A fresh clone stages a removed ledger file's calls again

- **WHEN** a run of the step has found a commit holding a ledger file that the step staged, whose calls were made with the repository root as their working directory, the person then removes that file with `git rm`, commits and pushes, and the session is then resumed in a fresh clone of that branch, at the same path, with no change of branch there before the agent's next commit
- **THEN** the agent's next commit there carries the calls that the removed file held

#### Scenario: A ledger file that a removal leaves is left to git

- **WHEN** the agent's commit took a ledger file that the step staged, that commit has a parent, a run of the step has found that commit checked out, and then, with that commit still checked out and that file in the working tree, the agent runs `git reset HEAD~1` or `git reset -N HEAD~1` alone, or the person removes that file from the index with `git rm --cached` and commits, and the step's next run comes before any other git command
- **THEN** after that run, the working tree still holds that file, the index still has no entry for it, or only the intent-to-add entry that `git reset -N` leaves, and no ledger file that the step stages later in that clone holds its calls

#### Scenario: A squash with a plain reset keeps its ledger files

- **WHEN** two of the agent's commits in a row took ledger files that the step staged, the first of them has a parent, a run of the step has found each of them checked out, no ignore rule matches the ledger path and no sparse checkout leaves it out, and then, with the second of them checked out, the agent runs `git reset HEAD~2` alone, and then `git add -A && git commit`, while no other git command holds the index
- **THEN** that commit holds both ledger files

#### Scenario: A ledger file comes back with a commit that its own command reset away

- **WHEN** the agent runs `git commit && git reset HEAD~1` alone, for a commit that has a parent and for which the step staged a ledger file, and then, with that commit's parent still checked out, runs a mixed `git reset` alone, back to that commit, while no other git command holds the index
- **THEN** after the run that follows that reset, the index and the working tree hold the file as that commit does, and the agent's next commit carries none of its calls

#### Scenario: A soft reset back to a commit that its own command reset away leaves its ledger file out

- **WHEN** the agent runs `git commit && git reset HEAD~1` alone, for a commit that has a parent and for which the step staged a ledger file, a run of the step then takes that file back from the working tree alone, and next, with that commit's parent still checked out and nothing having put the file in the index or the working tree since, the agent runs `git reset --soft` alone, back to that commit, while no other git command holds the index
- **THEN** after the run that follows that reset, neither the index nor the working tree holds the file, and no ledger file that the step stages there later holds its calls

#### Scenario: A put-back does not undo a staged removal

- **WHEN** a run of the step has found a commit holding a ledger file that the step staged, the person then removes that file from the index with `git rm --cached` and commits, the step's next run comes, and then `git reset --soft HEAD~1` runs alone, while no other git command holds the index
- **THEN** after the step's next run, the index still has no entry for that file, and the next commit there does not hold it unless a command adds the file again

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

A failure inside the capture step SHALL NOT stop or fail the agent's session. The registered command SHALL exit with success even when its script cannot be read or started, in each shell that Claude Code runs a hook's command in: `sh`, Git Bash on Windows, and PowerShell on Windows without Git Bash. The step SHALL print nothing on standard output, SHALL write no text taken from the transcript or the ledger to standard error, and SHALL finish within a time budget, leaving what it has not read for a later run. On failure it SHALL leave the ledger and its own records as they were.

#### Scenario: An unreadable transcript is skipped

- **WHEN** the transcript path the hook receives does not exist
- **THEN** the step exits with success and records nothing

#### Scenario: Capture never asks the agent to continue

- **WHEN** the step fails for any reason, including when its script cannot be read or started
- **THEN** the registered command exits with success and has printed nothing on standard output

#### Scenario: The registered command succeeds in PowerShell

- **WHEN** the registered command runs in Windows PowerShell or in PowerShell 7, as Claude Code runs a hook's command on Windows without Git Bash, and its script cannot be found or Python cannot be started
- **THEN** the command exits with success and prints nothing on standard output

#### Scenario: A failure message quotes nothing from the transcript

- **WHEN** a transcript line that cannot be read contains text
- **THEN** the message on standard error contains none of that text

#### Scenario: A long transcript does not hold up the session

- **WHEN** reading the transcript would take longer than the time budget
- **THEN** the step stops at the budget and exits with success, and a later run records the rest
