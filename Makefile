DOS2UNIX=$(shell which dos2unix || which fromdos)

clean:
	find . -name \*.pyc -exec rm {} \;
	find . -name coshsh.log -exec rm {} \;
	rm -f coshsh.tgz

pack:
	tar --exclude .git \
		--exclude Changelog \
		--exclude Makefile \
		--exclude README \
		--exclude README.asciidoc \
		--exclude README.de.asciidoc \
		--exclude TODO \
		--exclude test \
		--exclude coshsh.tgz \
		--exclude coshsh.log \
		-zcvf coshsh.tgz .

doc:
	cp -p README.asciidoc docs/README && cd docs && asciidoc --unsafe -a toc -a toclevels=2 -a max-width=800 README
	chmod 644 docs/README.html
	$(DOS2UNIX) docs/README.html
	$(RM) -f docs/README
