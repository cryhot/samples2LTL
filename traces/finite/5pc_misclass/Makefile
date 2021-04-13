SUBDIRS := $(shell ls -d */)
.DEFAULT_GOAL = generate

# call to subdirectories Makefiles

.PHONY: generate $(SUBDIRS:%=.generate@%)
generate: $(SUBDIRS:%=.generate@%)
$(SUBDIRS:%=.generate@%): .generate@%: %
	-$(MAKE) -C $< generate

.PHONY: clean $(SUBDIRS:%=.clean@%)
clean: $(SUBDIRS:%=.clean@%)
$(SUBDIRS:%=.clean@%): .clean@%: %
	-$(MAKE) -C $< clean
