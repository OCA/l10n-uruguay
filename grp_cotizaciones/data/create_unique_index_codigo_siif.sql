DROP INDEX IF EXISTS codigo_siif_uniq_idx;

CREATE UNIQUE INDEX codigo_siif_uniq_idx ON res_currency (codigo_siif) WHERE codigo_siif != 0;
