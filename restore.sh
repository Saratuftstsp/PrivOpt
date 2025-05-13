#!/bin/bash

psql << EOF
select nspname from pg_namespace where nspname='public';
analyze;