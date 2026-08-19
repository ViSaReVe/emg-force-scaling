.PHONY: all fetch prepare sweep plot clean check smoke inspect paired budget budget-tests plot-budget

all: fetch prepare sweep paired plot budget budget-tests plot-budget

check:      ## sanity-check paths, montage and one record before the long runs
	python -m src.fetch --check
	python -m src.dataset --check

smoke:      ## synthetic data, no download - proves the harness runs end to end
	python -m src.smoke

fetch:      ## download only the MVC + Random sub-datasets (~5 GB, not the full 143 GB)
	python -m src.fetch

prepare:    ## window, filter, featurise, MVC-normalise -> results/cache/*.npz  (add LIMIT=3 for a fast first pass)
	python -m src.dataset $(if $(LIMIT),--limit $(LIMIT))

inspect:    ## sanity-check the cache: normalisation, EMG-force relation, go/no-go fit
	python -m src.inspect

sweep:      ## leave-one-subject-out x training-set-size sweep
	python -m src.sweep

paired:     ## paired per-subject tests behind the headline claim
	python -m src.paired

plot:       ## the figure that goes in the email
	python -m src.plot

budget:     ## corpus size x calibration seconds - the decision surface (~5 min, needs `sweep` first)
	python -m src.budget

budget-tests: ## paired tests behind the budget claim
	python -m src.budget_tests

plot-budget:  ## the calibration-budget figure
	python -m src.plot_budget

clean:
	rm -rf results/cache results/*.csv results/*.png results/*.txt results/*.json
