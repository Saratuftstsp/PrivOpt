# Introduction
This project aims to study how noise addition can help make system catalogs more private when the server using it is untrusted. 
The main tool being used is the Postgres database management system. The python library psycopg2 is used to communicate with Postgres.

# Experiments
Currently, Laplace noise is being added to the 3rd, 5th and 21st columns in the pg_statistic, the main System Catalog table in Postgres.
These columns are related to the nullfrac, n_distinct and most_common_frequencies attributes, which appear in the public view
of pg_statistic called pg_stats. The names of the attributes are different in pg_statistic but comparing it with pg_stats shows that
the values are the same.

Noise is being added to these individually, and then queries for the JOB benchmark, setup for studied on query optimization, are run using the 
noisy statistic.

In order to create a truly private environment, all other fields of pg_statistic are set to 0 or null.

Runtimes are observed for the different cases of each attribute being noised, to see which attribute's noisy version affects runtimes the most.
