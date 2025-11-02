-- Adminer 5.4.1 PostgreSQL 17.6 dump

DROP TABLE IF EXISTS "posts";
DROP SEQUENCE IF EXISTS posts_id_seq;
CREATE SEQUENCE posts_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."posts" (
    "id" integer DEFAULT nextval('posts_id_seq') NOT NULL,
    "title" character varying(40) NOT NULL,
    "content" text NOT NULL,
    "filename" character varying(40),
    CONSTRAINT "posts_pkey" PRIMARY KEY ("id")
)
WITH (oids = false);


-- 2025-11-02 16:38:53 UTC
