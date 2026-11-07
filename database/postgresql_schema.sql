--
-- 智核 A12 PostgreSQL 当前数据库结构快照，导出日期：2026-10-10。
-- 来源：本机 postgres 数据库，public模式共16张业务表；不包含业务数据。
-- 使用 PostgreSQL 18 的 psql 导入新建的空数据库：
-- psql -U postgres -d 目标空数据库 -v ON_ERROR_STOP=1 -f postgresql_schema.sql
-- 服务器须先安装 pgvector 扩展文件（本机版本0.8.6）；脚本会 CREATE EXTENSION vector。
-- 包含字段、序列、主外键、约束、默认值、向量维度和HNSW索引。
-- 不复制原数据库的所有者和账号授权，避免新环境缺少原角色而导入失败。
-- 不删除已有表；不要直接导入正在使用的数据库。
-- PostgreSQL database dump
--

\restrict sVEgxekkbAppusePYEz1sXDjeh1xJkpxZ21soWdwRASB5a85pXWbNN7gEXfdGlo

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: a12_ai_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_ai_feedback (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80),
    project_id character varying(80),
    action character varying(32) NOT NULL,
    target_type character varying(32) DEFAULT 'presentation'::character varying NOT NULL,
    instruction text,
    change_summary text,
    before_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    after_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    event_id character varying(64)
);


--
-- Name: a12_ai_feedback_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_ai_feedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_ai_feedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_ai_feedback_id_seq OWNED BY public.a12_ai_feedback.id;


--
-- Name: a12_ai_run_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_ai_run_log (
    id bigint NOT NULL,
    run_id character varying(64) NOT NULL,
    user_id character varying(64),
    operation character varying(80) NOT NULL,
    model character varying(120),
    model_profile character varying(32),
    reasoning_effort character varying(32),
    status character varying(32) NOT NULL,
    latency_ms integer DEFAULT 0 NOT NULL,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    fallback_reason text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_ai_run_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_ai_run_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_ai_run_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_ai_run_log_id_seq OWNED BY public.a12_ai_run_log.id;


--
-- Name: a12_classroom_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_classroom_event (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    project_id character varying(80) NOT NULL,
    session_id character varying(80),
    student_key character varying(128),
    event_type character varying(32) NOT NULL,
    question_id character varying(128),
    answer text,
    correct boolean,
    response_ms integer,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    event_id character varying(64)
);


--
-- Name: a12_classroom_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_classroom_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_classroom_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_classroom_event_id_seq OWNED BY public.a12_classroom_event.id;


--
-- Name: a12_course_graph; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_course_graph (
    user_id character varying(64) NOT NULL,
    course_id character varying(80) NOT NULL,
    title character varying(255) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    graph_data jsonb NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_course_graph_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_course_graph_version (
    user_id character varying(64) NOT NULL,
    course_id character varying(80) NOT NULL,
    version integer NOT NULL,
    title character varying(255) NOT NULL,
    graph_data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_graph_evidence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_graph_evidence (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    course_id character varying(80) NOT NULL,
    resource_key character varying(180) NOT NULL,
    content_sha256 character varying(64) NOT NULL,
    node_id character varying(80) NOT NULL,
    excerpt text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_graph_evidence_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_graph_evidence_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_graph_evidence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_graph_evidence_id_seq OWNED BY public.a12_graph_evidence.id;


--
-- Name: a12_learning_video_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_learning_video_job (
    job_id character varying(32) NOT NULL,
    user_id character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'queued'::character varying NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    error text DEFAULT ''::text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    lease_id character varying(32)
);


--
-- Name: a12_outline_chat_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_outline_chat_message (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80) NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_outline_chat_message_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_outline_chat_message_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_outline_chat_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_outline_chat_message_id_seq OWNED BY public.a12_outline_chat_message.id;


--
-- Name: a12_outline_chat_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_outline_chat_session (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80) NOT NULL,
    title character varying(255),
    intent jsonb DEFAULT '{}'::jsonb NOT NULL,
    final_prompt text,
    outline_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    status character varying(30) DEFAULT 'active'::character varying NOT NULL,
    last_message_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_outline_chat_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_outline_chat_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_outline_chat_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_outline_chat_session_id_seq OWNED BY public.a12_outline_chat_session.id;


--
-- Name: a12_outline_generation_record; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_outline_generation_record (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80) NOT NULL,
    outline_id character varying(80),
    title character varying(255),
    final_prompt text,
    outline_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    slide_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_outline_generation_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_outline_generation_record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_outline_generation_record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_outline_generation_record_id_seq OWNED BY public.a12_outline_generation_record.id;


--
-- Name: a12_outline_strategy_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_outline_strategy_run (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80) NOT NULL,
    course_id character varying(80),
    strategy character varying(32) NOT NULL,
    graph_version integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_outline_strategy_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_outline_strategy_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_outline_strategy_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_outline_strategy_run_id_seq OWNED BY public.a12_outline_strategy_run.id;


--
-- Name: a12_resource_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_resource_index (
    resource_key text NOT NULL,
    source_type text NOT NULL,
    resource_id text NOT NULL,
    file_url text NOT NULL,
    file_fingerprint text NOT NULL,
    title text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    available boolean DEFAULT true NOT NULL,
    allow_ai boolean DEFAULT true NOT NULL,
    parse_status text DEFAULT 'pending'::text NOT NULL,
    error_message text,
    text_length integer DEFAULT 0 NOT NULL,
    chunk_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    indexed_at timestamp with time zone,
    CONSTRAINT ck_a12_resource_index_source CHECK ((source_type = ANY (ARRAY['public'::text, 'personal'::text, 'community'::text, 'temp'::text])))
);


--
-- Name: a12_resource_index_chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_resource_index_chunk (
    chunk_id text NOT NULL,
    resource_key text NOT NULL,
    source_type text NOT NULL,
    resource_id text NOT NULL,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    embedding_vector public.vector(1024),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_retrieval_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_retrieval_log (
    id bigint NOT NULL,
    query text NOT NULL,
    resource_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    match_count integer DEFAULT 0 NOT NULL,
    top_score double precision,
    search_mode text DEFAULT 'unknown'::text NOT NULL,
    latency_ms integer DEFAULT 0 NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_retrieval_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_retrieval_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_retrieval_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_retrieval_log_id_seq OWNED BY public.a12_retrieval_log.id;


--
-- Name: a12_teacher_style_memory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_teacher_style_memory (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    session_id character varying(80) NOT NULL,
    source_message text NOT NULL,
    extracted_style jsonb DEFAULT '{}'::jsonb NOT NULL,
    necessity_score numeric(5,4) DEFAULT 0 NOT NULL,
    reason character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_teacher_style_memory_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_teacher_style_memory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_teacher_style_memory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_teacher_style_memory_id_seq OWNED BY public.a12_teacher_style_memory.id;


--
-- Name: a12_teacher_style_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.a12_teacher_style_profile (
    id bigint NOT NULL,
    user_id character varying(64) NOT NULL,
    style_summary text,
    profile jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_count integer DEFAULT 0 NOT NULL,
    confidence numeric(5,4) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: a12_teacher_style_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.a12_teacher_style_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: a12_teacher_style_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.a12_teacher_style_profile_id_seq OWNED BY public.a12_teacher_style_profile.id;


--
-- Name: a12_ai_feedback id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_ai_feedback ALTER COLUMN id SET DEFAULT nextval('public.a12_ai_feedback_id_seq'::regclass);


--
-- Name: a12_ai_run_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_ai_run_log ALTER COLUMN id SET DEFAULT nextval('public.a12_ai_run_log_id_seq'::regclass);


--
-- Name: a12_classroom_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_classroom_event ALTER COLUMN id SET DEFAULT nextval('public.a12_classroom_event_id_seq'::regclass);


--
-- Name: a12_graph_evidence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_graph_evidence ALTER COLUMN id SET DEFAULT nextval('public.a12_graph_evidence_id_seq'::regclass);


--
-- Name: a12_outline_chat_message id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_message ALTER COLUMN id SET DEFAULT nextval('public.a12_outline_chat_message_id_seq'::regclass);


--
-- Name: a12_outline_chat_session id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_session ALTER COLUMN id SET DEFAULT nextval('public.a12_outline_chat_session_id_seq'::regclass);


--
-- Name: a12_outline_generation_record id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_generation_record ALTER COLUMN id SET DEFAULT nextval('public.a12_outline_generation_record_id_seq'::regclass);


--
-- Name: a12_outline_strategy_run id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_strategy_run ALTER COLUMN id SET DEFAULT nextval('public.a12_outline_strategy_run_id_seq'::regclass);


--
-- Name: a12_retrieval_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_retrieval_log ALTER COLUMN id SET DEFAULT nextval('public.a12_retrieval_log_id_seq'::regclass);


--
-- Name: a12_teacher_style_memory id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_memory ALTER COLUMN id SET DEFAULT nextval('public.a12_teacher_style_memory_id_seq'::regclass);


--
-- Name: a12_teacher_style_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_profile ALTER COLUMN id SET DEFAULT nextval('public.a12_teacher_style_profile_id_seq'::regclass);


--
-- Name: a12_ai_feedback a12_ai_feedback_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_ai_feedback
    ADD CONSTRAINT a12_ai_feedback_pkey PRIMARY KEY (id);


--
-- Name: a12_ai_run_log a12_ai_run_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_ai_run_log
    ADD CONSTRAINT a12_ai_run_log_pkey PRIMARY KEY (id);


--
-- Name: a12_classroom_event a12_classroom_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_classroom_event
    ADD CONSTRAINT a12_classroom_event_pkey PRIMARY KEY (id);


--
-- Name: a12_course_graph a12_course_graph_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_course_graph
    ADD CONSTRAINT a12_course_graph_pkey PRIMARY KEY (user_id, course_id);


--
-- Name: a12_course_graph_version a12_course_graph_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_course_graph_version
    ADD CONSTRAINT a12_course_graph_version_pkey PRIMARY KEY (user_id, course_id, version);


--
-- Name: a12_graph_evidence a12_graph_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_graph_evidence
    ADD CONSTRAINT a12_graph_evidence_pkey PRIMARY KEY (id);


--
-- Name: a12_graph_evidence a12_graph_evidence_user_id_course_id_resource_key_node_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_graph_evidence
    ADD CONSTRAINT a12_graph_evidence_user_id_course_id_resource_key_node_id_key UNIQUE (user_id, course_id, resource_key, node_id);


--
-- Name: a12_learning_video_job a12_learning_video_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_learning_video_job
    ADD CONSTRAINT a12_learning_video_job_pkey PRIMARY KEY (job_id);


--
-- Name: a12_outline_chat_message a12_outline_chat_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_message
    ADD CONSTRAINT a12_outline_chat_message_pkey PRIMARY KEY (id);


--
-- Name: a12_outline_chat_session a12_outline_chat_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_session
    ADD CONSTRAINT a12_outline_chat_session_pkey PRIMARY KEY (id);


--
-- Name: a12_outline_chat_session a12_outline_chat_session_user_id_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_session
    ADD CONSTRAINT a12_outline_chat_session_user_id_session_id_key UNIQUE (user_id, session_id);


--
-- Name: a12_outline_generation_record a12_outline_generation_record_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_generation_record
    ADD CONSTRAINT a12_outline_generation_record_pkey PRIMARY KEY (id);


--
-- Name: a12_outline_strategy_run a12_outline_strategy_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_strategy_run
    ADD CONSTRAINT a12_outline_strategy_run_pkey PRIMARY KEY (id);


--
-- Name: a12_outline_strategy_run a12_outline_strategy_run_user_id_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_strategy_run
    ADD CONSTRAINT a12_outline_strategy_run_user_id_session_id_key UNIQUE (user_id, session_id);


--
-- Name: a12_resource_index_chunk a12_resource_index_chunk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_resource_index_chunk
    ADD CONSTRAINT a12_resource_index_chunk_pkey PRIMARY KEY (chunk_id);


--
-- Name: a12_resource_index a12_resource_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_resource_index
    ADD CONSTRAINT a12_resource_index_pkey PRIMARY KEY (resource_key);


--
-- Name: a12_retrieval_log a12_retrieval_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_retrieval_log
    ADD CONSTRAINT a12_retrieval_log_pkey PRIMARY KEY (id);


--
-- Name: a12_teacher_style_memory a12_teacher_style_memory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_memory
    ADD CONSTRAINT a12_teacher_style_memory_pkey PRIMARY KEY (id);


--
-- Name: a12_teacher_style_profile a12_teacher_style_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_profile
    ADD CONSTRAINT a12_teacher_style_profile_pkey PRIMARY KEY (id);


--
-- Name: a12_teacher_style_profile a12_teacher_style_profile_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_profile
    ADD CONSTRAINT a12_teacher_style_profile_user_id_key UNIQUE (user_id);


--
-- Name: idx_a12_ai_feedback_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_ai_feedback_user ON public.a12_ai_feedback USING btree (user_id, created_at DESC);


--
-- Name: idx_a12_ai_run_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_ai_run_created ON public.a12_ai_run_log USING btree (created_at DESC);


--
-- Name: idx_a12_chat_message_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_chat_message_session ON public.a12_outline_chat_message USING btree (user_id, session_id, created_at);


--
-- Name: idx_a12_chat_session_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_chat_session_user ON public.a12_outline_chat_session USING btree (user_id, updated_at DESC);


--
-- Name: idx_a12_classroom_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_classroom_project ON public.a12_classroom_event USING btree (user_id, project_id, created_at DESC);


--
-- Name: idx_a12_graph_evidence_course; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_graph_evidence_course ON public.a12_graph_evidence USING btree (user_id, course_id, node_id);


--
-- Name: idx_a12_resource_chunk_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_resource_chunk_embedding_hnsw ON public.a12_resource_index_chunk USING hnsw (embedding_vector public.vector_cosine_ops);


--
-- Name: idx_a12_resource_chunk_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_resource_chunk_resource ON public.a12_resource_index_chunk USING btree (resource_key);


--
-- Name: idx_a12_resource_index_available; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_resource_index_available ON public.a12_resource_index USING btree (source_type, available, allow_ai);


--
-- Name: idx_a12_retrieval_log_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_retrieval_log_created ON public.a12_retrieval_log USING btree (created_at DESC);


--
-- Name: idx_a12_teacher_memory_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_teacher_memory_user ON public.a12_teacher_style_memory USING btree (user_id, created_at DESC);


--
-- Name: idx_a12_video_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_a12_video_queue ON public.a12_learning_video_job USING btree (status, created_at);


--
-- Name: uq_a12_ai_feedback_event; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_a12_ai_feedback_event ON public.a12_ai_feedback USING btree (event_id) WHERE (event_id IS NOT NULL);


--
-- Name: uq_a12_classroom_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_a12_classroom_event_id ON public.a12_classroom_event USING btree (event_id) WHERE (event_id IS NOT NULL);


--
-- Name: a12_outline_chat_message a12_outline_chat_message_user_id_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_chat_message
    ADD CONSTRAINT a12_outline_chat_message_user_id_session_id_fkey FOREIGN KEY (user_id, session_id) REFERENCES public.a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE;


--
-- Name: a12_outline_generation_record a12_outline_generation_record_user_id_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_outline_generation_record
    ADD CONSTRAINT a12_outline_generation_record_user_id_session_id_fkey FOREIGN KEY (user_id, session_id) REFERENCES public.a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE;


--
-- Name: a12_resource_index_chunk a12_resource_index_chunk_resource_key_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_resource_index_chunk
    ADD CONSTRAINT a12_resource_index_chunk_resource_key_fkey FOREIGN KEY (resource_key) REFERENCES public.a12_resource_index(resource_key) ON DELETE CASCADE;


--
-- Name: a12_teacher_style_memory a12_teacher_style_memory_user_id_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.a12_teacher_style_memory
    ADD CONSTRAINT a12_teacher_style_memory_user_id_session_id_fkey FOREIGN KEY (user_id, session_id) REFERENCES public.a12_outline_chat_session(user_id, session_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict sVEgxekkbAppusePYEz1sXDjeh1xJkpxZ21soWdwRASB5a85pXWbNN7gEXfdGlo

-- Agent prompt release schema 20261105
CREATE TABLE IF NOT EXISTS a12_prompt_version (
          id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,instruction TEXT NOT NULL DEFAULT '',
          layout_rule TEXT NOT NULL DEFAULT '',evidence JSONB NOT NULL DEFAULT '{}',
          parent_version BIGINT,created_by VARCHAR(64) NOT NULL,fingerprint TEXT UNIQUE,
          approved_by VARCHAR(64),approved_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

INSERT INTO a12_prompt_version(name,created_by,approved_by,approved_at,fingerprint)
           VALUES ('内置基线','system','system',NOW(),'builtin-v1') ON CONFLICT(fingerprint) DO NOTHING;

ALTER TABLE a12_prompt_version ADD COLUMN IF NOT EXISTS template_bundle JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS a12_prompt_release (
          id INT PRIMARY KEY CHECK(id=1),active_version BIGINT NOT NULL REFERENCES a12_prompt_version(id),
          canary_version BIGINT REFERENCES a12_prompt_version(id),canary_percent INT NOT NULL DEFAULT 0
          CHECK(canary_percent BETWEEN 0 AND 20),revision INT NOT NULL DEFAULT 1,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

INSERT INTO a12_prompt_release(id,active_version)
           SELECT 1,id FROM a12_prompt_version WHERE fingerprint='builtin-v1' ON CONFLICT(id) DO NOTHING;

CREATE TABLE IF NOT EXISTS a12_prompt_run (
          id VARCHAR(32) PRIMARY KEY,user_id VARCHAR(64) NOT NULL,version_id BIGINT NOT NULL REFERENCES a12_prompt_version(id),
          release_revision INT NOT NULL,cohort VARCHAR(16) NOT NULL,runtime_run_id VARCHAR(64),theme TEXT,
          status VARCHAR(20) NOT NULL DEFAULT 'running',created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),completed_at TIMESTAMPTZ);

CREATE INDEX IF NOT EXISTS idx_prompt_run_user ON a12_prompt_run(user_id,created_at DESC);

ALTER TABLE a12_prompt_run ADD COLUMN IF NOT EXISTS template_sha256 TEXT;

CREATE TABLE IF NOT EXISTS a12_prompt_outcome (
          id BIGSERIAL PRIMARY KEY,run_id VARCHAR(32) NOT NULL REFERENCES a12_prompt_run(id),
          action VARCHAR(32) NOT NULL,event_key VARCHAR(100) NOT NULL,project_id VARCHAR(80),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),UNIQUE(run_id,event_key));

CREATE TABLE IF NOT EXISTS a12_prompt_release_history (
          id BIGSERIAL PRIMARY KEY,actor VARCHAR(64) NOT NULL,action VARCHAR(20) NOT NULL,reason TEXT NOT NULL,
          before_state JSONB NOT NULL,after_state JSONB NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

-- Public source patrol history (20261105)
CREATE TABLE IF NOT EXISTS a12_public_source_patrol (
 id BIGSERIAL PRIMARY KEY,actor VARCHAR(64) NOT NULL,checked_count INT NOT NULL,
 warning_count INT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

-- Batch planning and generation (20261105)
CREATE TABLE IF NOT EXISTS a12_batch_plan (
            id VARCHAR(32) PRIMARY KEY,user_id VARCHAR(64) NOT NULL,session_id VARCHAR(80),
            revision INT NOT NULL DEFAULT 1,status VARCHAR(20) NOT NULL DEFAULT 'draft',payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE TABLE IF NOT EXISTS a12_batch_job (
            id VARCHAR(32) PRIMARY KEY REFERENCES a12_batch_plan(id),user_id VARCHAR(64) NOT NULL,title TEXT NOT NULL,
            theme TEXT NOT NULL,status VARCHAR(24) NOT NULL DEFAULT 'queued',zip_status VARCHAR(24) NOT NULL DEFAULT 'idle',
            zip_error TEXT NOT NULL DEFAULT '',zip_lease VARCHAR(32),zip_updated_at TIMESTAMPTZ,
            include_partial BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE TABLE IF NOT EXISTS a12_batch_item (
            id VARCHAR(32) PRIMARY KEY,batch_id VARCHAR(32) NOT NULL REFERENCES a12_batch_job(id),user_id VARCHAR(64) NOT NULL,
            item_order INT NOT NULL,title TEXT NOT NULL,payload JSONB NOT NULL,output JSONB NOT NULL DEFAULT '{}',
            status VARCHAR(24) NOT NULL DEFAULT 'queued',stage TEXT NOT NULL DEFAULT '等待生成',progress INT NOT NULL DEFAULT 0,
            attempts INT NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',project_id INT,lease_id VARCHAR(32),
            next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE INDEX IF NOT EXISTS idx_batch_owner ON a12_batch_job(user_id,created_at DESC);

CREATE INDEX IF NOT EXISTS idx_batch_queue ON a12_batch_item(status,next_attempt_at,created_at);
