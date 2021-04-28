## Notice

This project is a fork from [gergia/samples2LTL](https://github.com/gergia/samples2LTL).
It implements the following features:
- finite traces support (generation, solvers input)
- MaxSAT extension of the simple SAT method
  (can be referred as `MaxSAT-flie` in the literature)
- a new top-down constructed decision tree approach
  (can be referred as `MaxSAT-DT` in the literature)

---

# traces2LTL
[![Python package](https://github.com/cryhot/samples2LTL/actions/workflows/pythonpackage.yaml/badge.svg)](https://github.com/cryhot/samples2LTL/actions/workflows/pythonpackage.yaml)

The goal is to learn an LTL formula that separates set of positive (P) and negative (N) traces. The resulting formula should be a model for every trace in P and should not be a model for any of the traces from N.
There are three methods in this repository:
- one that encodes the problem as a satisfiability of Boolean formula and gives it to Z3 solver
  ([`SAT-flie`](#running-sat-method))
  - this method has a MaxSAT alternative ([`MaxSAT-flie`](#running-maxsat-method))
- one that is based on decision tree learning from `SAT-flie` executed on subsets of the initial sample ([`SAT-DT`](#running-decision-tree-method-based-on-sat)).
- one that is based on decision tree learning from `MaxSAT-flie` in a top-down approach ([`MaxSAT-DT`](#running-decision-tree-method-based-on-maxsat)).

<!-- Webdemo is available at [flie.mpi-sws.org](https://flie.mpi-sws.org/) -->

## Setup
- setup a virtualenvironment for python 3.6 ([link](http://virtualenvwrapper.readthedocs.io/en/latest/)) and activate it (`workon ...`)
- run `pip install -r requirements.txt` to qinstall all necessary python packages available from pip
- install Z3 with python bindings ([link](https://github.com/Z3Prover/z3#python))

## Running

This toolbox has different features:
- [traces generation](#generating-traces):
  generate test traces
- [solvers](#running-solvers):
  LTL formula inference from traces
- [large-scale testing](#large-scale-testing):
  running [solvers](#running-solvers) on a whole benchmark of traces.
- [additional executables](#additional-executables): tests, etc



### Generating Traces

Generated traces have described [further below](#experiment-trace-file-format).
By default, generated traces are infinite, unless `--finite_traces` flag is specified.

<details>
<summary><code>./generateTestFiles.py --help</code></summary>
<p>

```
usage: generateTestFiles.py [-h] [--output_folder OUTPUTFOLDER]
                            [--counter_start COUNTERSTART]
                            [--pattern_files PATTERNFILE [PATTERNFILE ...]]
                            [--equal_number_accepting_rejecting]
                            [--traces_set_sizes TRACESSETSIZES [TRACESSETSIZES ...]]
                            [--trace_lengths TRACELENGTHS [TRACELENGTHS ...]]
                            [--num_files NUMFILES [NUMFILES ...]]
                            [--finite_traces]
                            [--misclassification_rate MISCLASSIFICATIONRATE]

optional arguments:
  -h, --help            show this help message and exit
  --output_folder OUTPUTFOLDER
  --counter_start COUNTERSTART
  --pattern_files PATTERNFILE [PATTERNFILE ...]
  --equal_number_accepting_rejecting
  --traces_set_sizes TRACESSETSIZES [TRACESSETSIZES ...]
  --trace_lengths TRACELENGTHS [TRACELENGTHS ...]
  --num_files NUMFILES [NUMFILES ...]
  --finite_traces
  --misclassification_rate MISCLASSIFICATIONRATE
```
</p>
</details>


### Running Solvers

to test on a single example (set of positive and negative traces), run `./experiment.py`.

<details>
<summary><code>./experiment.py --help</code></summary>
<p>

```
usage: experiment.py [-h] [-f TRACESFILENAME] [--test_sat_method]
                     [--test_dt_method] [--test_rec_dt]
                     [--misclassification R] [--start_depth I] [--max_depth I]
                     [--iteration_step I] [--optimize_depth I]
                     [--optimize {count,ratio}] [--min_score S]
                     [--max_num_formulas N] [--timeout T] [--log LVL]

optional arguments:
  -h, --help            show this help message and exit
  -f TRACESFILENAME, --traces TRACESFILENAME
  --test_sat_method
  --test_dt_method
  --test_rec_dt
  --misclassification R
                        formula should have a misclassification <= R
  --timeout T           timeout in seconds
  --log LVL             log level, usually in DEBUG, INFO, WARNING, ERROR,
                        CRITICAL

sat method arguments:
  --start_depth I       formula start at size I
  --max_depth I         search for formula of size < I
  --iteration_step I    increment formula size by I at each iteration
  --optimize_depth I    use optimizer for formula size >= I
  --optimize {count,ratio}
                        score to optimize
  --min_score S         formula should achieve a score >= S
  --max_num_formulas N
```
</p>
</details>

#### Running SAT method
```sh
./experiment.py --test_sat_method ...
```

#### Running MaxSAT method
```sh
./experiment.py --test_sat_method --optimize_depth=1 ...
```
For example, for inferring an LTL with up to 10% misclassification on sample `test.trace`:
 ```sh
./experiment.py -f test.trace --test_sat_method --optimize_depth=1 --optimize=count --min_score=0.9
```

#### Running decision tree method based on SAT
```sh
./experiment.py --test_dt_method ...
```


#### Running decision tree method based on MaxSAT
```sh
./experiment.py --test_rec_dt <MaxSAT args> ...
```
For example, for inferring an LTL with up to 10% misclassification on sample `test.trace` (with arbitrary `--min_score`):
```sh
./experiment.py -f test.trace --test_rec_dt --misclassification=0.1 --optimize_depth=1 --optimize=ratio --min_score=0.8
```

### Large-scale Testing

Use `./queue_maker.py enqueue` to run a solver on a whole benchmark on a Redis server (or locally if `--run-in-place` specified).
Then use `./queue_maker.py compile json` to compile all the results.

<details>
<summary><code>./queue_maker.py enqueue --help</code></summary>
<p>

```
usage: queue_maker.py enqueue [-h] [-f DIR] [-T T] [--shutdown-timeout T]
                              [--output-folder-format DIRNAME]
                              [--output-file-format BASENAME] [--enqueue]
                              [--dry-run] [--run-in-place]
                              (--test {SAT-DT,MaxSAT,SAT,MaxSAT-DT} | --test_sat_method | --test_maxsat_method | --test_sat_dt_method | --test_maxsat_dt_method)
                              [--misclassification R] [--start_depth I]
                              [--max_depth I] [--iteration_step I]
                              [--optimize_depth I] [--optimize {count,ratio}]
                              [--min_score S] [--log LVL]

run a batch of simulations

optional arguments:
  -h, --help            show this help message and exit
  --test {SAT-DT,MaxSAT,SAT,MaxSAT-DT}
                        shortcut for the following 4 methods
  --test_sat_method     Neider and Gavran SAT based algorithm
  --test_maxsat_method  ATVA MaxSAT based algorithm
  --test_sat_dt_method, --test_dt_method
                        Neider and Gavran Decision tree based on SAT
  --test_maxsat_dt_method, --test_rec_dt
                        ATVA Decision tree based on MaxSAT
  --misclassification R
  --log LVL             log level, usually in DEBUG, INFO, WARNING, ERROR,
                        CRITICAL

multiprocessing arguments:
  -f DIR, --traces_folder DIR
                        trace file/folder to run
  -T T, --timeout T     timeout in seconds
  --shutdown-timeout T  additionnal time given to the process to shut itself
                        down before killing it (default: 10+timeout/10
                        seconds)
  --output-folder-format DIRNAME
                        Output folder (default is where the trace is). Can
                        contain such formats: {method}, {argshash}, {ext},
                        {tracesdir}, {tracesname}, {tracesext},
                        {optimizeDepth}, {maxDepth}, {minScore}, {startDepth},
                        {optimize}, {timeout}, {step}, {misclassification}.
  --output-file-format BASENAME
                        Possible formats are {method}, {argshash}, {ext},
                        {tracesdir}, {tracesname}, {tracesext},
                        {optimizeDepth}, {maxDepth}, {minScore}, {startDepth},
                        {optimize}, {timeout}, {step}, {misclassification}.
  --enqueue             Enqueue to Redis (default).
  --dry-run             Just print commands.
  --run-in-place        Run directly, without multiprocessing.

sat/maxsat method arguments:
  --start_depth I       formula start at size I
  --max_depth I         search for formula of size < I
  --iteration_step I    increment formula size by I at each iteration
  --optimize_depth I    use optimizer for formula size >= I
  --optimize {count,ratio}
                        score to optimize
  --min_score S         formula should achieve a score > S

note: certain argument can take multiple value at the same time. Certain
parameters can even accept ranges of values (start:stop[:step]). For example,
you can specify: --min_score .5:.7:.025 --min_score .7,.8,.95 If multiple
parameters are multivalued, the cartesian product is made.
```
</p>
</details>

<details>
<summary><code>./queue_maker.py compile json --help</code></summary>
<p>

```
usage: queue_maker.py compile json [-h] [-f DIR] [--extension EXT] [-o FILE]
                                   [--header] [--no-header] [--filter EXPR]
                                   [--replace-traces SRC:DST]
                                   [COL:EXPR [COL:EXPR ...]]

Compile simulation results from json to csv. It's recommended to use a config
file for arguments, that can be called with @args.txt (one argument per line).

optional arguments:
  -h, --help            show this help message and exit
  -f DIR, --traces_folder DIR
                        folder where the traces results to compile are.
  --extension EXT       trace extension (default: .out.json)
  -o FILE, --output_file FILE
                        file to store the compiled results

output csv arguments:
  --header
  --no-header
  --filter EXPR         keep only traces where EXPR evaluates to True
  --replace-traces SRC:DST
                        replace traces from SRC subdirectories by the ones in
                        DST (applies after --filter)
  COL:EXPR              Columns of the output csv file"

EXPR must be a python expression. Run parameters can be accessed by:
algo.args.minScore, run.sucess, result.nSub etc. The variables sample and
formula are also available.
```
</p>
</details>

One can use one or multiple files containing arguments `./queue_maker.py compile json ... @args.txt`:
<details>
<summary>example of <code>args.txt</code></summary>
<p>

```
--traces_folder=all_traces/
--filter=           "/perfect/" in traces.filename
--filter=           algo.name == "MaxSAT"
--filter=           algo.args.minScore == 0.9
--filter=           run.success
--replace=few_traces/perfect:few_traces/misclass-5
--replace=few_traces/misclass-5:few_traces/perfect
tracesfile:         traces.filename
LTL_pattern_class:  traces.filename.split('/')[3]
LTL_pattern:        sample.possibleSolution
benchmark:          traces.filename.split('/')[2]
benchmark_noise:    {'perfect': 0, 'misclass-5': 0.05}[traces.filename.split('/')[2]]
sample_size:        len(sample)
sample_pos_size:    len(sample.positive)
sample_neg_size:    len(sample.negative)
algo:               algo.name
algo_score:         algo.args.optimize
algo_min_score:     algo.args.minScore
algo_misclass:      algo.args.misclassification
runtime:            run.time if run else algo.args.timeout
success:            int(bool(run.success))
LTL_size:           formula      and formula.getNumberOfSubformulas()
LTL_depth:          formula      and formula.getDepth()
DT_size:            decisionTree and decisionTree.getSize()
DT_depth:           decisionTree and decisionTree.getDepth()
```
</p>
</details>

### Additional executables

> _These executables were from previous version and are not guaranteed to work_

- to test on set of examples, one can run `python measureSolvingTime.py` with `--test_dt_method` or `--test_sat_method` and with the path to the folder containing the examples provided as an argument `--test_traces_folder`
- running `python measureSolvingTime.py --test_dt_method --test_sat_method` with no additional parameters takes the traces from `traces/generatedTest` and produces results in `experiments/test/`
- additionally, to make sure everything runs as it should one can run `pytest`




## Experiment Trace File Format
Experiment traces file consists of:
  - accepted traces
  - rejected traces
  - operators that a program can use
  - max depth to explore
  - the expected formula that describes this trace

An example trace looks like this
`1,1;1,0;0,1::1` and means that there are two variables (`x0` and `x1`) whose values in different timesteps are
 - x0 : 1,(1,0)*  
 - x1: 1,(0,1)*

 The value after separator `::` denotes the start of lasso that is being repeated forever. If it is missing, it assumes that the whole sequence is finite.
