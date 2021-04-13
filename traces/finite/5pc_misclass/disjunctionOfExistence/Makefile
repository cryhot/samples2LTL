D_SAMPLE2LTL ?= ../../../..
GENERATE_TEST_FILES ?= python3 $(D_SAMPLE2LTL)/generateTestFiles.py
D_PATTERNS ?= $(D_SAMPLE2LTL)/formulas/patterns
PATTERNS_FILE ?= $(D_PATTERNS)/disjunctionOfExistence.txt

.DEFAULT_GOAL=generate
.PHONY: generate clean

generate: clean
	$(GENERATE_TEST_FILES) --output_folder "./" --pattern_files $(PATTERNS_FILE) --finite_traces --misclassification_rate 0.05

clean:
	rm -f *.trace
