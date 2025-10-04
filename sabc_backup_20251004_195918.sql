--
-- PostgreSQL database dump
--

\restrict XO4jusQcMSXQC6G1Rg0g7VjAeKDeHPC1nBXCPdck3ufZFMqiNVu0OFvvTQHARXw

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: anglers; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.anglers (
    id integer NOT NULL,
    name text NOT NULL,
    email text,
    member boolean DEFAULT true,
    is_admin boolean DEFAULT false,
    password_hash text,
    year_joined integer,
    phone text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.anglers OWNER TO sabc_user;

--
-- Name: events; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.events (
    id integer NOT NULL,
    date date NOT NULL,
    year integer NOT NULL,
    name text NOT NULL,
    description text,
    event_type text DEFAULT 'sabc_tournament'::text,
    start_time time without time zone,
    weigh_in_time time without time zone,
    lake_name text,
    ramp_name text,
    entry_fee numeric DEFAULT 25.00,
    is_cancelled boolean DEFAULT false,
    holiday_name text,
    CONSTRAINT events_event_type_check CHECK ((event_type = ANY (ARRAY['sabc_tournament'::text, 'holiday'::text, 'other_tournament'::text, 'club_event'::text])))
);


ALTER TABLE public.events OWNER TO sabc_user;

--
-- Name: results; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.results (
    id integer NOT NULL,
    tournament_id integer,
    angler_id integer,
    num_fish integer DEFAULT 0,
    total_weight numeric DEFAULT 0.0,
    big_bass_weight numeric DEFAULT 0.0,
    dead_fish_penalty numeric DEFAULT 0.0,
    disqualified boolean DEFAULT false,
    buy_in boolean DEFAULT false,
    place_finish integer,
    was_member boolean DEFAULT true
);


ALTER TABLE public.results OWNER TO sabc_user;

--
-- Name: tournaments; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.tournaments (
    id integer NOT NULL,
    event_id integer,
    poll_id integer,
    name text NOT NULL,
    lake_id integer,
    ramp_id integer,
    lake_name text,
    ramp_name text,
    start_time time without time zone,
    end_time time without time zone,
    fish_limit integer DEFAULT 5,
    entry_fee numeric DEFAULT 25.00,
    is_team boolean DEFAULT true,
    is_paper boolean DEFAULT false,
    big_bass_carryover numeric DEFAULT 0.0,
    complete boolean DEFAULT false,
    created_by integer,
    limit_type text DEFAULT 'angler'::text,
    aoy_points boolean DEFAULT true
);


ALTER TABLE public.tournaments OWNER TO sabc_user;

--
-- Name: tournament_standings; Type: VIEW; Schema: public; Owner: sabc_user
--

CREATE VIEW public.tournament_standings AS
 SELECT t.id AS tournament_id,
    a.name AS angler_name,
    a.id AS angler_id,
    r.num_fish,
    (r.total_weight - r.dead_fish_penalty) AS final_weight,
    r.big_bass_weight,
    r.disqualified,
    r.buy_in,
    rank() OVER (PARTITION BY t.id ORDER BY
        CASE
            WHEN (r.disqualified = true) THEN (0)::numeric
            WHEN (r.buy_in = true) THEN (0)::numeric
            ELSE (r.total_weight - r.dead_fish_penalty)
        END DESC) AS place,
        CASE
            WHEN (r.disqualified = true) THEN (0)::bigint
            WHEN (r.buy_in = true) THEN GREATEST((0)::bigint, (( SELECT (101 - count(*))
               FROM public.results r2
              WHERE ((r2.tournament_id = t.id) AND ((r2.total_weight - r2.dead_fish_penalty) > (0)::numeric) AND (r2.disqualified = false) AND (r2.buy_in = false))) - 4))
            WHEN ((r.total_weight - r.dead_fish_penalty) = (0)::numeric) THEN GREATEST((0)::bigint, (( SELECT (101 - count(*))
               FROM public.results r2
              WHERE ((r2.tournament_id = t.id) AND ((r2.total_weight - r2.dead_fish_penalty) > (0)::numeric) AND (r2.disqualified = false) AND (r2.buy_in = false))) - 2))
            ELSE (101 - rank() OVER (PARTITION BY t.id ORDER BY (r.total_weight - r.dead_fish_penalty) DESC))
        END AS points
   FROM ((public.tournaments t
     JOIN public.results r ON ((t.id = r.tournament_id)))
     JOIN public.anglers a ON ((r.angler_id = a.id)))
  WHERE ((t.complete = true) AND (a.member = true));


ALTER VIEW public.tournament_standings OWNER TO sabc_user;

--
-- Name: angler_of_year; Type: VIEW; Schema: public; Owner: sabc_user
--

CREATE VIEW public.angler_of_year AS
 SELECT e.year,
    a.name,
    a.id AS angler_id,
    sum(ts.points) AS total_points,
    count(DISTINCT t.id) AS tournaments_fished,
    sum(ts.final_weight) AS total_weight,
    max(r.big_bass_weight) AS biggest_bass,
    rank() OVER (PARTITION BY e.year ORDER BY (sum(ts.points)) DESC) AS yearly_rank
   FROM ((((public.tournaments t
     JOIN public.events e ON ((t.event_id = e.id)))
     JOIN public.tournament_standings ts ON ((t.id = ts.tournament_id)))
     JOIN public.results r ON (((t.id = r.tournament_id) AND (ts.angler_id = r.angler_id))))
     JOIN public.anglers a ON ((r.angler_id = a.id)))
  WHERE ((t.complete = true) AND (a.member = true))
  GROUP BY e.year, a.id, a.name
  ORDER BY e.year DESC, (sum(ts.points)) DESC;


ALTER VIEW public.angler_of_year OWNER TO sabc_user;

--
-- Name: anglers_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.anglers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.anglers_id_seq OWNER TO sabc_user;

--
-- Name: anglers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.anglers_id_seq OWNED BY public.anglers.id;


--
-- Name: calendar_events; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.calendar_events (
    id integer NOT NULL,
    title text NOT NULL,
    event_date date NOT NULL,
    event_type text NOT NULL,
    description text,
    created_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT calendar_events_event_type_check CHECK ((event_type = ANY (ARRAY['holiday'::text, 'sabc_tournament'::text, 'other_tournament'::text])))
);


ALTER TABLE public.calendar_events OWNER TO sabc_user;

--
-- Name: calendar_events_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.calendar_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calendar_events_id_seq OWNER TO sabc_user;

--
-- Name: calendar_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.calendar_events_id_seq OWNED BY public.calendar_events.id;


--
-- Name: dues; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.dues (
    id integer NOT NULL,
    angler_id integer,
    year integer NOT NULL,
    amount numeric DEFAULT 25.00,
    paid_date date,
    paid boolean DEFAULT false
);


ALTER TABLE public.dues OWNER TO sabc_user;

--
-- Name: dues_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.dues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dues_id_seq OWNER TO sabc_user;

--
-- Name: dues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.dues_id_seq OWNED BY public.dues.id;


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_id_seq OWNER TO sabc_user;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: lakes; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.lakes (
    id integer NOT NULL,
    yaml_key text NOT NULL,
    display_name text NOT NULL,
    google_maps_iframe text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.lakes OWNER TO sabc_user;

--
-- Name: lakes_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.lakes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lakes_id_seq OWNER TO sabc_user;

--
-- Name: lakes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.lakes_id_seq OWNED BY public.lakes.id;


--
-- Name: news; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.news (
    id integer NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    author_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    published boolean DEFAULT false,
    priority integer DEFAULT 0,
    expires_at timestamp without time zone,
    last_edited_by integer
);


ALTER TABLE public.news OWNER TO sabc_user;

--
-- Name: news_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.news_id_seq OWNER TO sabc_user;

--
-- Name: news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.news_id_seq OWNED BY public.news.id;


--
-- Name: officer_positions; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.officer_positions (
    id integer NOT NULL,
    angler_id integer,
    "position" text NOT NULL,
    year integer NOT NULL,
    elected_date date
);


ALTER TABLE public.officer_positions OWNER TO sabc_user;

--
-- Name: officer_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.officer_positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.officer_positions_id_seq OWNER TO sabc_user;

--
-- Name: officer_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.officer_positions_id_seq OWNED BY public.officer_positions.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    used_at timestamp without time zone
);


ALTER TABLE public.password_reset_tokens OWNER TO sabc_user;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.password_reset_tokens_id_seq OWNER TO sabc_user;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: poll_options; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.poll_options (
    id integer NOT NULL,
    poll_id integer,
    option_text text NOT NULL,
    option_data text,
    display_order integer DEFAULT 0
);


ALTER TABLE public.poll_options OWNER TO sabc_user;

--
-- Name: poll_options_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.poll_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_options_id_seq OWNER TO sabc_user;

--
-- Name: poll_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.poll_options_id_seq OWNED BY public.poll_options.id;


--
-- Name: poll_votes; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.poll_votes (
    id integer NOT NULL,
    poll_id integer,
    option_id integer,
    angler_id integer,
    voted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.poll_votes OWNER TO sabc_user;

--
-- Name: poll_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.poll_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_votes_id_seq OWNER TO sabc_user;

--
-- Name: poll_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.poll_votes_id_seq OWNED BY public.poll_votes.id;


--
-- Name: polls; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.polls (
    id integer NOT NULL,
    title text NOT NULL,
    description text,
    poll_type text NOT NULL,
    event_id integer,
    created_by integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    starts_at timestamp without time zone NOT NULL,
    closes_at timestamp without time zone NOT NULL,
    closed boolean DEFAULT false,
    multiple_votes boolean DEFAULT false,
    winning_option_id integer
);


ALTER TABLE public.polls OWNER TO sabc_user;

--
-- Name: polls_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.polls_id_seq OWNER TO sabc_user;

--
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
-- Name: ramps; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.ramps (
    id integer NOT NULL,
    lake_id integer,
    name text NOT NULL,
    google_maps_iframe text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ramps OWNER TO sabc_user;

--
-- Name: ramps_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.ramps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ramps_id_seq OWNER TO sabc_user;

--
-- Name: ramps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.ramps_id_seq OWNED BY public.ramps.id;


--
-- Name: results_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.results_id_seq OWNER TO sabc_user;

--
-- Name: results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.results_id_seq OWNED BY public.results.id;


--
-- Name: team_results; Type: TABLE; Schema: public; Owner: sabc_user
--

CREATE TABLE public.team_results (
    id integer NOT NULL,
    tournament_id integer,
    angler1_id integer,
    angler2_id integer,
    total_weight numeric DEFAULT 0.0,
    place_finish integer
);


ALTER TABLE public.team_results OWNER TO sabc_user;

--
-- Name: team_results_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.team_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.team_results_id_seq OWNER TO sabc_user;

--
-- Name: team_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.team_results_id_seq OWNED BY public.team_results.id;


--
-- Name: tournaments_id_seq; Type: SEQUENCE; Schema: public; Owner: sabc_user
--

CREATE SEQUENCE public.tournaments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tournaments_id_seq OWNER TO sabc_user;

--
-- Name: tournaments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: sabc_user
--

ALTER SEQUENCE public.tournaments_id_seq OWNED BY public.tournaments.id;


--
-- Name: anglers id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.anglers ALTER COLUMN id SET DEFAULT nextval('public.anglers_id_seq'::regclass);


--
-- Name: calendar_events id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.calendar_events ALTER COLUMN id SET DEFAULT nextval('public.calendar_events_id_seq'::regclass);


--
-- Name: dues id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.dues ALTER COLUMN id SET DEFAULT nextval('public.dues_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: lakes id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.lakes ALTER COLUMN id SET DEFAULT nextval('public.lakes_id_seq'::regclass);


--
-- Name: news id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.news ALTER COLUMN id SET DEFAULT nextval('public.news_id_seq'::regclass);


--
-- Name: officer_positions id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.officer_positions ALTER COLUMN id SET DEFAULT nextval('public.officer_positions_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: poll_options id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.poll_options ALTER COLUMN id SET DEFAULT nextval('public.poll_options_id_seq'::regclass);


--
-- Name: poll_votes id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.poll_votes ALTER COLUMN id SET DEFAULT nextval('public.poll_votes_id_seq'::regclass);


--
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- Name: ramps id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.ramps ALTER COLUMN id SET DEFAULT nextval('public.ramps_id_seq'::regclass);


--
-- Name: results id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.results ALTER COLUMN id SET DEFAULT nextval('public.results_id_seq'::regclass);


--
-- Name: team_results id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.team_results ALTER COLUMN id SET DEFAULT nextval('public.team_results_id_seq'::regclass);


--
-- Name: tournaments id; Type: DEFAULT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.tournaments ALTER COLUMN id SET DEFAULT nextval('public.tournaments_id_seq'::regclass);


--
-- Data for Name: anglers; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.anglers (id, name, email, member, is_admin, password_hash, year_joined, phone, created_at) FROM stdin;
378	Eric Vasquez	envasquez@icloud.com	t	t	\N	\N	+15127509358	2025-09-29 13:35:59.228382
365	Albert Hudson	hud1979@sbcglobal.net	f	f	\N	\N	+15126582596	2025-09-29 13:35:59.216915
366	Austin Vanalli	austinvanalli@gmail.com	t	f	\N	\N	+15124366923	2025-09-29 13:35:59.217762
367	Austyn Manos	amanos7189@gmail.com	f	f	\N	\N	+15129448573	2025-09-29 13:35:59.218657
368	Ben Rumsey	bendonrum@gmail.com	f	f	\N	\N	+17373005746	2025-09-29 13:35:59.220025
369	Bobby Whiteside	bwhiteside@austin.rr.com	f	f	\N	\N	+15127541964	2025-09-29 13:35:59.220975
370	Caleb Glomb	caleb@trade-ready.com	t	f	\N	\N	+15127051435	2025-09-29 13:35:59.221872
372	Coleman Cunningham	colemancunningham53@gmail.com	t	f	\N	\N	+15127899052	2025-09-29 13:35:59.22357
373	Dale Hawkins	hawkinsd1@hotmail.com	f	f	\N	\N	+15126364184	2025-09-29 13:35:59.22435
374	Dallas Foster	fosterdallas90@gmail.com	f	f	\N	\N	+15122214095	2025-09-29 13:35:59.225176
377	Elliot Thompson	Slowboyiq2@gmail.com	f	f	\N	\N	+15124700076	2025-09-29 13:35:59.227656
379	Eric Pittman	coachepittman@gmail.com	f	f	\N	\N	+19792496381	2025-09-29 13:35:59.229137
380	Ethan Cole	ecolizer11@gmail.com	f	f	\N	\N	+15128154214	2025-09-29 13:35:59.229887
381	Glen Fisseler	guest@gmail.com	f	f	\N	\N	+15122223499	2025-09-29 13:35:59.230732
382	Hank Fleming	hankgun@sbcglobal.net	t	f	\N	\N	+15127059055	2025-09-29 13:35:59.23153
383	Henry Meyer	Ehenrymeyerjr@gmail.com	t	f	\N	\N	+15125693138	2025-09-29 13:35:59.232263
384	James Guest	Temp_1@gmail.com	f	f	\N	\N	+15122895477	2025-09-29 13:35:59.233064
385	Jeddy Rumsey	gerardrumsey@gmail.com	t	f	\N	\N	+17372102187	2025-09-29 13:35:59.233932
386	Jeremy West	jewest@taylormorrison.com	t	f	\N	\N	+12543003182	2025-09-29 13:35:59.234752
387	Jim Cottingham	guest@guest.com	f	f	\N	\N	+15122895477	2025-09-29 13:35:59.235526
388	Jimmy Daugherty	jdaugherty3@twc.com	f	f	\N	\N	+15129830705	2025-09-29 13:35:59.236286
390	John Simmons	Calldrsimmons1@gmail.com	f	f	\N	\N	+15127995322	2025-09-29 13:35:59.237721
391	Josh Lasseter	jlasseter09@gmail.com	t	f	\N	\N	+15126295681	2025-09-29 13:35:59.238479
392	Kent Harris	k5harris@sbcglobal.net	t	f	\N	\N	+15129246906	2025-09-29 13:35:59.239309
393	Kirk McGlamery	kirkm72@att.net	t	f	\N	\N	+15126733505	2025-09-29 13:35:59.240077
394	Lane Grigg	Lgrigg@eanesisd.net	f	f	\N	\N	+15124269534	2025-09-29 13:35:59.240785
396	Matt Hohertz	mhohertz9@gmail.com	f	f	\N	\N	+15122898024	2025-09-29 13:35:59.242128
397	Michael Wagner	Mikebwagner@yahoo.com	f	f	\N	\N	+15125799203	2025-09-29 13:35:59.24288
398	Michael Domotor	micheal.domotor52@gmail.com	f	f	\N	\N	+15126306656	2025-09-29 13:35:59.243808
399	Mike Wagner	mikebwagner_1@yahoo.com	f	f	\N	\N	+15125799203	2025-09-29 13:35:59.244676
400	Nick Fisseler	nfisseler@gmail.com	f	f	\N	\N	+17135038654	2025-09-29 13:35:59.245652
402	Noel Taylor	ntaylor@vikingfence.com	f	f	\N	\N	+15125555555	2025-09-29 13:35:59.247981
403	Patrick Gillilan	patrick@leviathanrods.com	f	f	\N	\N	+18172699800	2025-09-29 13:35:59.248928
404	Pete Trevino	bassangler1930@gmail.com	f	f	\N	\N	+15124969961	2025-09-29 13:35:59.249796
405	Randy Scott	randalrscott@gmail.com	f	f	\N	\N	+15128094634	2025-09-29 13:35:59.250674
406	Reuben Rountree	seaborn46@gmail.com	f	f	\N	\N	+15125546103	2025-09-29 13:35:59.251547
408	Robbie Hawkins	rpchawk@aol.com	t	f	\N	\N	+17376103562	2025-09-29 13:35:59.253265
409	Robert Whitehead	robertwhitehead555@gmail.com	t	f	\N	\N	+15122172346	2025-09-29 13:35:59.254123
410	Scott Turner	skeetot2016@gmail.com	f	f	\N	\N	+15124567890	2025-09-29 13:35:59.255072
411	Seabo Rountree	seaborn46_1@gmail.com	t	f	\N	\N	+15125546103	2025-09-29 13:35:59.256143
412	Stan Kaminski	stankaminski@earthlink.net	f	f	\N	\N	+15124132641	2025-09-29 13:35:59.257088
413	Stephen Graham	Grahamstephen88@gmail.com	f	f	\N	\N	+15127314192	2025-09-29 13:35:59.258021
414	Steve Nardecchia	steve_nardecchia@saustinbc.com	f	f	\N	\N	\N	2025-09-29 13:35:59.259035
415	Stevie Montague	stevie_montague@saustinbc.com	f	f	\N	\N	+15124567890	2025-09-29 13:35:59.260065
416	System Account	sabc@gmail.com	f	f	\N	\N	+15125555555	2025-09-29 13:35:59.261002
418	Thomas Corallo	corallothomas@gmail.com	t	f	\N	\N	+15126398798	2025-09-29 13:35:59.26304
419	Thomas Carrell	carrellthomas81@gmail.com	f	f	\N	\N	+15122151401	2025-09-29 13:35:59.264577
420	Tommy Nanyes	tnanyes@gmail.com	f	f	\N	\N	+15128797180	2025-09-29 13:35:59.2655
421	Tony Dieterich	Tonydieterich@yahoo.com	f	f	\N	\N	+15129255390	2025-09-29 13:35:59.266411
422	Van Trahern	vtrahern@gmail.com	f	f	\N	\N	+15129227932	2025-09-29 13:35:59.267333
371	Chris Annoni	ceegarnut@aol.com	t	f	\N	\N	+15122895477	2025-09-29 13:35:59.222739
363	Aaron Haynes	ahaynes7891@gmail.com	f	f	\N	\N	+19562998902	2025-09-29 13:35:59.214712
407	Rob Bunce	rbunce@austin.rr.com	t	t	\N	\N	+15126584152	2025-09-29 13:35:59.25241
417	Terry Kyle	tkyle1950@yahoo.com	t	f	\N	\N	+15126635695	2025-09-29 13:35:59.261981
395	Lee Martinez	hooligangamc@gmail.com	t	f	\N	\N	+13614434318	2025-09-29 13:35:59.241454
278	SABC Admin	admin@sabc.com	t	t	$2b$12$w88nO67/q/ySnEAyrVIkD.p31fp3Z.kLl8sWRUNNxLnZrwomBiKoO	2024	\N	2025-09-29 13:19:25.04203
364	Adam Clark	awclark1980@gmail.com	t	f	\N	\N	+15124229142	2025-09-29 13:35:59.216012
423	Vinh Vuong	vsquared162@gmail.com	f	f	\N	\N	+15125479165	2025-09-29 13:35:59.268207
424	Woody TB	TBD_2@gmail.com	f	f	\N	\N	+15124567890	2025-09-29 13:35:59.269213
375	Darryl Ackerman	darrly_ackerman@saustinbc.com	t	f	\N	\N	+15122895477	2025-09-29 13:35:59.225986
\.


--
-- Data for Name: calendar_events; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.calendar_events (id, title, event_date, event_type, description, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: dues; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.dues (id, angler_id, year, amount, paid_date, paid) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.events (id, date, year, name, description, event_type, start_time, weigh_in_time, lake_name, ramp_name, entry_fee, is_cancelled, holiday_name) FROM stdin;
137	2023-01-22	2023	January 2023 Tournament	Event #1	sabc_tournament	06:00:00	15:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
145	2023-02-26	2023	February 2025 Tournament	Event #2	sabc_tournament	06:00:00	15:00:00	Lake Belton	cedar ridge park	25.0	f	\N
146	2023-03-26	2023	March 2023 Tournament	Event #3	sabc_tournament	06:00:00	15:00:00	Lake Buchanan	Burnett County Park	25.0	f	\N
148	2023-05-21	2023	May 2023 Tournament	Event #5	sabc_tournament	06:00:00	15:00:00	Still House Hollow Lake	riversbend park	25.0	f	\N
149	2023-06-25	2023	June 2023 Tournament	Event #6	sabc_tournament	05:00:00	13:00:00	Lake Buchanan	Burnett County Park	25.0	f	\N
151	2023-08-27	2023	August 2023 Tournament	Event #8	sabc_tournament	00:00:00	09:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
150	2023-07-23	2023	July 2023 Tournament	Event #7	sabc_tournament	00:00:00	09:00:00	Lake Austin	loop 360 boat ramp	25.0	f	\N
152	2023-09-24	2023	September 2023 Tournament	Event #9	sabc_tournament	07:00:00	15:00:00	Still House Hollow Lake	riversbend park	25.0	f	\N
153	2023-10-22	2023	October 2025 Tournament	Event #10	sabc_tournament	07:00:00	15:00:00	Canyon Lake	canyon lake boat ramp 17	25.0	f	\N
154	2023-11-19	2023	November 2023 Tournament	Event #11	sabc_tournament	06:00:00	15:00:00	Lake Travis	tournament point	25.0	f	\N
155	2023-12-03	2023	December 2023 Tournament	Event #12	sabc_tournament	06:00:00	15:00:00	Lake Austin	loop 360 boat ramp	25.0	f	\N
147	2023-04-23	2023	April 2023 Tournament	Event #4	sabc_tournament	06:00:00	15:00:00	Lake Travis	tournament point	25.0	f	\N
156	2024-01-28	2024	January 2024 Tournament	Event #1	sabc_tournament	07:00:00	16:00:00	Lake Buchanan	burnett county park	25.0	f	\N
157	2024-02-25	2024	February 2024 Tournament	Event #2	sabc_tournament	07:00:00	15:00:00	Lake Travis	tournament point	25.0	f	\N
158	2024-03-24	2024	March 2024 Tournament	Event #3	sabc_tournament	06:30:00	16:00:00	Lake Travis	tournament point	25.0	f	\N
159	2024-04-28	2024	April 2024 Tournament	Event #4	sabc_tournament	06:30:00	15:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
160	2024-05-19	2024	May 2024 Tournament	Event #5	sabc_tournament	06:00:00	15:00:00	Lake Buchanan	burnett county park	25.0	f	\N
161	2024-06-23	2024	June 2024 Tournament	Event #6	sabc_tournament	00:00:00	09:00:00	Lake Travis	tournament point	25.0	f	\N
162	2024-07-28	2024	July 2024 Tournament	Event #7	sabc_tournament	00:00:00	09:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
163	2024-08-25	2024	August 2024 Tournament	Event #8	sabc_tournament	06:00:00	13:00:00	Still House Hollow Lake	riversbend park	25.0	f	\N
164	2024-09-22	2024	September 2024 Tournament	Event #9	sabc_tournament	06:30:00	15:00:00	Lake Belton	cedar ridge park	25.0	f	\N
165	2024-10-27	2024	October 2024 Tournament	Event #10	sabc_tournament	06:30:00	14:30:00	Lake Buchanan	burnett county park	25.0	f	\N
166	2024-11-24	2024	November 2024 Tournament	Event #11	sabc_tournament	06:30:00	14:30:00	Lake LBJ	yacht club & marina	25.0	f	\N
167	2024-12-08	2024	December 2024 Tournament	Event #12	sabc_tournament	06:00:00	15:00:00	Inks Lake	Inks Lake State Park	25.0	f	\N
168	2025-01-26	2025	January 2025 Tournament	Event #1	sabc_tournament	07:00:00	16:00:00	Fayette County Reservoir	oak thicket park	25.0	f	\N
169	2025-02-23	2025	February 2025 Tournament	Event #2	sabc_tournament	07:00:00	15:00:00	Lake Buchanan	burnett county park	25.0	f	\N
170	2025-03-23	2025	March 2025 Tournament	Event #3	sabc_tournament	07:00:00	16:00:00	Lake Travis	tournament point	25.0	f	\N
171	2025-04-27	2025	April 2025 Tournament	Event #4	sabc_tournament	06:30:00	15:30:00	Still House Hollow Lake	riversbend park	25.0	f	\N
172	2025-05-18	2025	May 2025 Tournament	Event #5	sabc_tournament	06:15:00	15:30:00	Lake Travis	tournament point	25.0	f	\N
173	2025-06-22	2025	June 2025 Tournament	Event #6	sabc_tournament	00:00:00	09:00:00	Lake Travis	tournament point	25.0	f	\N
175	2025-09-08	2025	September 2025 Tournament	Event #9	sabc_tournament	06:30:00	15:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
174	2025-08-24	2025	August 2025 Tournament	Event #8	sabc_tournament	05:00:00	11:00:00	Lake Travis	mansfield dam	25.0	f	\N
176	2025-01-01	2025	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
177	2025-01-20	2025	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
178	2025-02-17	2025	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
179	2025-05-25	2025	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
180	2025-07-04	2025	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
181	2025-09-01	2025	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
182	2025-11-11	2025	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
183	2025-11-27	2025	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
184	2025-12-25	2025	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
185	2026-01-01	2026	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
186	2026-01-19	2026	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
187	2026-02-16	2026	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
188	2026-05-31	2026	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
189	2026-07-04	2026	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
190	2026-09-07	2026	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
191	2026-11-11	2026	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
192	2026-11-26	2026	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
193	2026-12-25	2026	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
194	2027-01-01	2027	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
195	2027-01-18	2027	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
196	2027-02-15	2027	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
197	2027-05-30	2027	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
198	2027-07-04	2027	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
199	2027-09-06	2027	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
200	2027-11-11	2027	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
201	2027-11-25	2027	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
202	2027-12-25	2027	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
203	2028-01-01	2028	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
204	2028-01-17	2028	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
205	2028-02-21	2028	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
206	2028-05-28	2028	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
207	2028-07-04	2028	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
208	2028-09-04	2028	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
209	2028-11-11	2028	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
210	2028-11-23	2028	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
211	2028-12-25	2028	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
212	2029-01-01	2029	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
213	2029-01-15	2029	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
214	2029-02-19	2029	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
215	2029-05-27	2029	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
216	2029-07-04	2029	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
217	2029-09-03	2029	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
218	2029-11-11	2029	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
219	2029-11-22	2029	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
220	2029-12-25	2029	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
221	2030-01-01	2030	New Year's Day	Federal Holiday: New Year's Day	holiday	\N	\N	\N	\N	25.00	f	New Year's Day
222	2030-01-21	2030	Martin Luther King Jr. Day	Federal Holiday: Martin Luther King Jr. Day	holiday	\N	\N	\N	\N	25.00	f	Martin Luther King Jr. Day
223	2030-02-18	2030	Presidents Day	Federal Holiday: Presidents Day	holiday	\N	\N	\N	\N	25.00	f	Presidents Day
224	2030-05-26	2030	Memorial Day	Federal Holiday: Memorial Day	holiday	\N	\N	\N	\N	25.00	f	Memorial Day
225	2030-07-04	2030	Independence Day	Federal Holiday: Independence Day	holiday	\N	\N	\N	\N	25.00	f	Independence Day
226	2030-09-02	2030	Labor Day	Federal Holiday: Labor Day	holiday	\N	\N	\N	\N	25.00	f	Labor Day
227	2030-11-11	2030	Veterans Day	Federal Holiday: Veterans Day	holiday	\N	\N	\N	\N	25.00	f	Veterans Day
228	2030-11-28	2030	Thanksgiving Day	Federal Holiday: Thanksgiving Day	holiday	\N	\N	\N	\N	25.00	f	Thanksgiving Day
229	2030-12-25	2030	Christmas Day	Federal Holiday: Christmas Day	holiday	\N	\N	\N	\N	25.00	f	Christmas Day
\.


--
-- Data for Name: lakes; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.lakes (id, yaml_key, display_name, google_maps_iframe, created_at) FROM stdin;
1	belton	Lake Belton	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d127649.34820671633!2d-97.51757425844599!3d31.19291265081045!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864542e4f58c375d%3A0x7a72ea4037ea61e1!2sBelton%20Lake!5e0!3m2!1sen!2sus!4v1672084069808!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.751455
3	travis	Lake Travis	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d220097.1104179962!2d-98.20472670546498!3d30.46394666079379!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b234b3c3d1495%3A0x74e585eef7396b82!2sLake%20Travis!5e0!3m2!1sen!2sus!4v1672084358820!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.755607
4	inks	Inks Lake	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27432.80686924699!2d-98.40580282633022!3d30.743668309010552!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865afbdc61d5e785%3A0x73a6c3855a5925bb!2sInks%20Lake!5e0!3m2!1sen!2sus!4v1672084568730!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.757076
5	lbj	Lake LBJ	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d109851.72687261835!2d-98.4610429014146!3d30.63772073331308!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865afde4a00a34eb%3A0xb4e89bc100df5a25!2sLake%20Lyndon%20B.%20Johnson!5e0!3m2!1sen!2sus!4v1672084656844!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.758577
6	austin	Lake Austin	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d110184.25020196816!2d-97.9221557584372!3d30.343621887024348!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3435dbfe386d%3A0x7036e55ce0332d2e!2sLake%20Austin!5e0!3m2!1sen!2sus!4v1672085066104!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.759907
7	bastrop	Lake Bastrop	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27599.1678513568!2d-97.29475782718627!3d30.154389796074234!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644901016f7a4a5%3A0x5fc6b59e59a6c4f9!2sLake%20Bastrop!5e0!3m2!1sen!2sus!4v1672086620966!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.761227
9	buchanan	Lake Buchanan	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d109664.49492179992!2d-98.48687604745601!3d30.802200572804807!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865af9e0edbb56fb%3A0x7f0e121dabc72896!2sBuchanan%20Lake!5e0!3m2!1sen!2sus!4v1672089611108!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.76406
13	sommerville	Lake Sommerville	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d110214.29386216452!2d-96.66790740907118!3d30.31692288719605!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644179fc687c36d%3A0x38e930b57f6b5861!2sSomerville%20Lake!5e0!3m2!1sen!2sus!4v1672090809093!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.770446
14	canyon	Canyon Lake	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d221420.26450043847!2d-98.39890081314753!3d29.873165763891397!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865c9bbea40ad011%3A0xba6571b88cb898b1!2sCanyon%20Lake%2C%20TX!5e0!3m2!1sen!2sus!4v1672091127799!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.772027
15	waco	Lake Waco	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d54404.788625262685!2d-97.2601439798701!3d31.54339997858495!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f85b47cb24f0d%3A0xa837658ad93f16aa!2sLake%20Waco!5e0!3m2!1sen!2sus!4v1672091839394!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.773624
11	marble_falls	Lake Marble Falls	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d54969.84203714589!2d-98.33216078575335!3d30.560176174262416!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b1cb83373ba9b%3A0xe8ac7b0555be6e17!2sLake%20Marble%20Falls!5e0!3m2!1sen!2sus!4v1672090387181!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.767246
16	choke_canyon	Choke Canyon Reservior	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d112201.98522502766!2d-98.428165500817!3d28.50025816256284!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865d7c7c81e064a7%3A0x8618346548101157!2sChoke%20Canyon%20Reservoir!5e0!3m2!1sen!2sus!4v1672093258979!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.775356
8	fayette_county	Fayette County Reservoir	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27661.073845959945!2d-96.75088302750409!3d29.932430634478603!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8643f4db8073adb9%3A0x80c9b433b95b7331!2sFayette%20County%20Reservoir!5e0!3m2!1sen!2sus!4v1672086798689!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.762538
10	stillhouse	Still House Hollow Lake	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d218842.65828602808!2d-97.87295436793148!3d31.01464251415014!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8645382293747367%3A0xa006fdf3c27114e9!2sStillhouse%20Hollow%20Lake!5e0!3m2!1sen!2sus!4v1672089803444!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.765734
2	decker	Lake Walter E. Long (Decker)	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27557.76355476698!2d-97.63664045612765!3d30.302019155659053!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644b8067b2dfc2b%3A0x2ec27edf62c402e8!2sLake%20Walter%20E.%20Long!5e0!3m2!1sen!2sus!4v1672084291654!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.753751
12	lady_bird	Lady Bird Lake	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d55134.06585531003!2d-97.78582748745764!3d30.26902532158024!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644b50e720134c3%3A0x9eb67ecc9e2fcb81!2sLady%20Bird%20Lake!5e0!3m2!1sen!2sus!4v1672090163822!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 15:47:27.768845
\.


--
-- Data for Name: news; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.news (id, title, content, author_id, created_at, updated_at, published, priority, expires_at, last_edited_by) FROM stdin;
1	New Site!	Our new website is up and active. Key changes are: We can vote on everything (and anything) 100% on-line! We've added Latest News section, for updates to the site! Look at the Polls section for voting on tournament details and club motions. Yay!	278	2025-09-29 22:00:25.915866	2025-09-30 21:26:36.696757	t	0	\N	278
\.


--
-- Data for Name: officer_positions; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.officer_positions (id, angler_id, "position", year, elected_date) FROM stdin;
1	364	Vice President	2025	2025-09-29
2	378	Technology Director	2025	2025-09-29
3	371	President	2025	2025-09-29
4	371	Treasurer	2025	2025-09-29
5	407	Secretary	2025	2025-09-29
6	417	Tournament Director	2025	2025-09-29
7	395	Assistant Tournament Director	2025	2025-09-29
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.password_reset_tokens (id, user_id, token, expires_at, used, created_at, used_at) FROM stdin;
\.


--
-- Data for Name: poll_options; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.poll_options (id, poll_id, option_text, option_data, display_order) FROM stdin;
\.


--
-- Data for Name: poll_votes; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.poll_votes (id, poll_id, option_id, angler_id, voted_at) FROM stdin;
\.


--
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.polls (id, title, description, poll_type, event_id, created_by, created_at, starts_at, closes_at, closed, multiple_votes, winning_option_id) FROM stdin;
\.


--
-- Data for Name: ramps; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.ramps (id, lake_id, name, google_maps_iframe, created_at) FROM stdin;
1	1	cedar ridge park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d4321.177367944409!2d-97.4569861346852!3d31.16781644035503!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864543757eb30125%3A0x17fbcbdab7568631!2sCedar%20Ridge%20Park%20Campground!5e0!3m2!1sen!2sus!4v1672084176691!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.056147
2	1	temple lake park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3415.1679938270418!2d-97.49716678513832!3d31.132848973290137!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x86454163a9dc3bfd%3A0xee022161ce3aacd5!2sTemple%20Lake%20Park!5e0!3m2!1sen!2sus!4v1672084210091!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.059735
3	1	blora	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3414.8360503697413!2d-97.55820148513804!3d31.14206757284069!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8645442e47a0eaf7%3A0xebb32443ccd8abff!2sBLORA!5e0!3m2!1sen!2sus!4v1672084237455!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.061549
4	2	walter e. long metropolitan park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27557.76355476698!2d-97.63664045612765!3d30.302019155659053!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644b8067b2dfc2b%3A0x2ec27edf62c402e8!2sLake%20Walter%20E.%20Long!5e0!3m2!1sen!2sus!4v1672084291654!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.063753
5	3	mansfield dam	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3441.5586222547017!2d-97.90956088515522!3d30.39188890903085!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b312583cad291%3A0xa528bfb289afe63c!2sMansfield%20Dam%2C%20Austin%2C%20TX%2078734!5e0!3m2!1sen!2sus!4v1672084422898!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.066247
7	3	tournament point	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3439.3832948444756!2d-98.0145139851538!3d30.4535798060842!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3b25686dd915%3A0x666bb94d3587abc9!2sTournament%20Point!5e0!3m2!1sen!2sus!4v1672084502896!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.069435
9	5	yacht club & marina	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3435.92021707728!2d-98.33944238515157!3d30.551558101393322!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b0368e3e45e11%3A0x2a3445d322a5846d!2sLake%20LBJ%20Yacht%20Club%20%26%20Marina!5e0!3m2!1sen!2sus!4v1672084726827!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.074945
10	5	blue briar	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3434.4566669683177!2d-98.39695698515064!3d30.592879999410872!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b0227a6b45b99%3A0x2930a76d8b5602fc!2sBluebriar%20Park%2C%20Granite%20Shoals%2C%20TX%2078654!5e0!3m2!1sen!2sus!4v1672084758039!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.076986
11	5	mcnair park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3434.8114244978537!2d-98.41854248515084!3d30.582868399891495!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b019f2df91893%3A0x508cc0e4abaee81b!2sMcNair%20Park!5e0!3m2!1sen!2sus!4v1672084791944!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.078752
12	6	loop 360 boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3442.99412354953!2d-97.79878258515609!3d30.35111691097542!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b34da5ad510af%3A0xc87465991d57c4da!2sLoop%20360%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672086035327!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.081223
13	6	emma long metropolitan park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3443.806141712739!2d-97.84411658515658!3d30.32803151207547!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3453575fee85%3A0xcd23194b656e6ca8!2sEmma%20Long%20Metropolitan%20Park!5e0!3m2!1sen!2sus!4v1672086108658!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.082928
14	6	walsh boat landing	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d4917.111458641186!2d-97.7893092423146!3d30.295845726521364!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644caaa979797e5%3A0x2f0106edaa298fbe!2sWalsh%20Boat%20Landing!5e0!3m2!1sen!2sus!4v1672086236126!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.084585
15	7	south shore park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27599.1678513568!2d-97.29475782718627!3d30.154389796074234!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x86449aa0cd896375%3A0xf320e3207416fdbb!2sLake%20Bastrop%20South%20Shore%20Park!5e0!3m2!1sen!2sus!4v1672086643870!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.087194
16	7	north shore park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d12522.596645779417!2d-97.28674063100424!3d30.160612426065434!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644903dbb0946d1%3A0xf0e7a524c5329569!2sLake%20Bastrop%20North%20Shore%20Park!5e0!3m2!1sen!2sus!4v1672086678318!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.088955
8	4	Inks Lake State Park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3429.323908811455!2d-98.37325277952323!3d30.737401842334435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865afb95d363f72f%3A0xc99d574116003081!2sInks%20Lake%20State%20Park!5e0!3m2!1sen!2sus!4v1672084604980!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.072278
17	8	prairie preserve park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27661.073845959945!2d-96.75088302750409!3d29.932430634478603!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8643f52b52c35b67%3A0xee48924556306a0!2sLake%20Fayette%20Prairie%20Preserve!5e0!3m2!1sen!2sus!4v1672086847620!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.091581
18	8	oak thicket park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27661.073845959945!2d-96.75088302750409!3d29.932430634478603!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8643f5190809f8ab%3A0x1d4d26ed97836313!2sLake%20Fayette%20Oak%20Thicket%20Park!5e0!3m2!1sen!2sus!4v1672086887598!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.093348
20	9	black rock park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d109664.49492179992!2d-98.486876047456!3d30.802200572804807!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865af85a3ae40745%3A0xd371c1f327b446d4!2sBlack%20Rock%20Park!5e0!3m2!1sen!2sus!4v1672089697157!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.097511
21	10	riversbend park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d10367.10477023927!2d-97.60476446416581!3d31.002028052248534!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x86453828b3e31e89%3A0xdc4172db44cc2571!2sRiversbend%20Park%2C%20Salado%2C%20TX%2076571!5e0!3m2!1sen!2sus!4v1672089832988!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.09991
22	10	union grove park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d41468.41908095708!2d-97.60476446416581!3d31.002028052248534!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864537ead456dc99%3A0xe91af0e473c273d9!2sUnion%20Grove%20Park%2C%20Stillhouse%20Lake!5e0!3m2!1sen!2sus!4v1672089883488!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.101477
23	10	cedar gap park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d41468.128093465006!2d-97.64223182453333!3d31.002697114757016!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864537ca15b176b1%3A0xb9ad15c37447b25a!2sCedar%20Gap%20Park!5e0!3m2!1sen!2sus!4v1672089940210!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.103034
24	10	stillhouse hollow marina	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d8836.008883776529!2d-97.54428504907642!3d31.038106554721605!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864538a668df90b9%3A0x72c86bc08a507c74!2sStillhouse%20Hollow%20Marina!5e0!3m2!1sen!2sus!4v1672089997591!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.104639
25	11	cottonwood shores boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d17394.33793171148!2d-98.33192875205326!3d30.561694151333096!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b033786282987%3A0x19fbfcd9892adc36!2sCottonwood%20Shores%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672090755070!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.106905
26	12	festival beach boat '	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2181.2854596206494!2d-97.7288438446887!3d30.24815874702227!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644b44c2bc61e85%3A0x2cb2edce77cd129e!2sFestival%20Beach%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672090270049!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.109107
27	13	welch park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d6886.949258183686!2d-96.55590269321215!3d30.337480469022637!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x8644185d1c2da391%3A0xd297242da6453f9a!2sWelch%20Park%20Somerville%20Lake!5e0!3m2!1sen!2sus!4v1672090907382!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.111502
28	13	nails creek boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d13779.834854683037!2d-96.68050825595857!3d30.29523695720339!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x86441543bd5e1ef3%3A0x5e31bfa0864d895b!2sNails%20Creek%20boat%20ramp!5e0!3m2!1sen!2sus!4v1672090951159!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.113178
29	13	lake somerville state park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d55113.257421752896!2d-96.69698774650007!3d30.306056337662877!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864416ed609b6de3%3A0xf30fd18ac3e6c4d!2sLake%20Somerville%20State%20Park!5e0!3m2!1sen!2sus!4v1672091005194!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.115047
30	14	potters creek launch ramp/dock	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d11552.672974119347!2d-98.28253103063459!3d29.90691571725766!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b629b348f2d53%3A0x6f200d4d67f5ff94!2sPotters%20Creek%20Launch%20Ramp%2FDock%2C%20Potters%20Creek%20Park%20Rd%2C%20Canyon%20Lake%2C%20TX%2078133!5e0!3m2!1sen!2sus!4v1672091266095!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.117932
31	14	boat ramp 22	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d11552.672974119347!2d-98.28253103063459!3d29.90691571725766!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b637fc3b970cf%3A0x64f4331cd30e6090!2sBoat%20Ramp%20%2322!5e0!3m2!1sen!2sus!4v1672091297198!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.119688
32	14	canyon lake boat ramp 3	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d46214.352132814245!2d-98.31887084297465!3d29.8990247019628!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x428db388dab28bcb!2sCanyon%20Lake%20Boat%20Ramp%203!5e0!3m2!1sen!2sus!4v1672091363282!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.121384
33	14	canyon lake boat ramp 17	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d11553.90502733395!2d-98.22608605371178!3d29.8962906611298!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865c9f8fecaacb99%3A0x8e07759997303507!2sCanyon%20Lake%20Boat%20Ramp%2017!5e0!3m2!1sen!2sus!4v1672091431845!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.123271
34	14	canyon lake marina	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d11553.400710212505!2d-98.2337912410377!3d29.900640236290005!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x47f30bb3803074d7!2sCanyon%20Lake%20Marina!5e0!3m2!1sen!2sus!4v1672091472046!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.124977
35	14	canyon lake boat ramp 10	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d53095.50046207343!2d-98.29323685555411!3d29.88184221518331!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x9c8f0a393ca925d0!2sCanyon%20Lake%20Boat%20Ramp%2010!5e0!3m2!1sen!2sus!4v1672091528095!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.126462
36	15	lake waco marina boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27198.848846719997!2d-97.26907074451448!3d31.555563414770422!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f85841fbf9ccb%3A0x56d4418c4261a9!2sLake%20Waco%20Marina%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672093070081!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.128767
37	15	airport park boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27189.14416508598!2d-97.25525200366978!3d31.588835799615612!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f858e0d5c6615%3A0x3853416863e4376a!2sAirport%20Park%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672093102880!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.130279
38	15	airport park boat ramp 2	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27189.14416508598!2d-97.25525200366978!3d31.588835799615612!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f85bc49f71cd9%3A0xa43edf02cf85c93e!2sAirport%20Park%20Boat%20Ramp%20%232!5e0!3m2!1sen!2sus!4v1672093151544!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.131948
39	15	airport park boat ramp 3	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27189.14416508598!2d-97.25525200366978!3d31.588835799615612!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f853f831f3f6f%3A0x6005816b3d3c8679!2sAirport%20Park%20Boat%20Ramp%20%233!5e0!3m2!1sen!2sus!4v1672093170646!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.133365
40	15	flat rock boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d27184.033585972033!2d-97.30261981487271!3d31.606344734538432!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x864f9001a2a0c7ff%3A0x2f059105abf40ade!2sFlat%20Rock%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672093196862!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.134759
41	16	south shore unit boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d112201.98522502766!2d-98.428165500817!3d28.50025816256284!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865d630da9d40927%3A0x3c8382a711edbf7e!2sSouth%20Shore%20Unit%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672093321362!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.136741
42	16	calliham unit boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d14027.864601918014!2d-98.3590442724813!3d28.480566030578192!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865d7df1db5b9e31%3A0x8744286541b9eb12!2sCalliham%20Unit%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672093406309!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.138881
43	30	Loop 360 Boat Ramp	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3442.99412354953!2d-97.79878258515609!3d30.35111691097542!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b34da5ad510af%3A0xc87465991d57c4da!2sLoop%20360%20Boat%20Ramp!5e0!3m2!1sen!2sus!4v1672086035327!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:07:48.902046
44	32	Inks Lake State Park	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3429.323908811455!2d-98.37325277952323!3d30.737401842334435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865afb95d363f72f%3A0xc99d574116003081!2sInks%20Lake%20State%20Park!5e0!3m2!1sen!2sus!4v1672084604980!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:08:07.979208
45	25	Collier Cove Boat Ramp-Lake Travis	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3439.1326665894044!2d-98.03029128515358!3d30.46068020574459!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3b4bb7873ea5%3A0xb6a53b9c3f3d023c!2sCollier%20Cove%20Boat%20Ramp-Lake%20Travis!5e0!3m2!1sen!2sus!4v1672084465961!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:08:08.00857
46	22	Lake LBJ Yacht Club & Marina	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3435.92021707728!2d-98.33944238515157!3d30.551558101393322!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b0368e3e45e11%3A0x2a3445d322a5846d!2sLake%20LBJ%20Yacht%20Club%20%26%20Marina!5e0!3m2!1sen!2sus!4v1672084726827!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:08:08.034703
6	3	collier cove boat ramp	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3439.1326665894044!2d-98.03029128515358!3d30.46068020574459!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3b4bb7873ea5%3A0xb6a53b9c3f3d023c!2sCollier%20Cove%20Boat%20Ramp-Lake%20Travis!5e0!3m2!1sen!2sus!4v1672084465961!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.067834
47	24	Burnet County Park	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3425.388032374857!2d-98.39148858514476!3d30.84780938712895!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865af0da18d79f59%3A0x45d7ba50b57a98b7!2sBurnet%20County%20Park!5e0!3m2!1sen!2sus!4v1672089657639!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:08:08.078225
48	25	Tournament Point	<iframe allowfullscreen="" height="300" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3439.3832948444756!2d-98.0145139851538!3d30.4535798060842!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865b3b25686dd915%3A0x666bb94d3587abc9!2sTournament%20Point!5e0!3m2!1sen!2sus!4v1672084502896!5m2!1sen!2sus" style="border:0;" width="400"></iframe>	2025-09-20 22:08:08.133461
19	9	burnett county park	<iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3425.388032374857!2d-98.39148858514476!3d30.84780938712895!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x865af0da18d79f59%3A0x45d7ba50b57a98b7!2sBurnet%20County%20Park!5e0!3m2!1sen!2sus!4v1672089657639!5m2!1sen!2sus' width='100%' height='100%' style='border:0;' allowfullscreen='' loading='lazy' referrerpolicy='no-referrer-when-downgrade'></iframe>	2025-09-20 16:07:05.095851
\.


--
-- Data for Name: results; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.results (id, tournament_id, angler_id, num_fish, total_weight, big_bass_weight, dead_fish_penalty, disqualified, buy_in, place_finish, was_member) FROM stdin;
1931	134	364	5	15.09	5.60	0.00	f	f	\N	t
1932	134	385	0	0.00	0.00	0.00	f	f	\N	t
1936	134	382	0	0.00	0.00	0.00	f	f	\N	t
1937	134	383	4	8.36	0.00	0.00	f	f	\N	t
1929	134	409	5	11.05	0	0	f	f	\N	t
1938	134	365	1	0.84	0	0	f	f	\N	t
1933	134	400	2	4.65	0	0	f	f	\N	t
1934	134	396	3	6.49	0	0	f	f	\N	t
1939	134	391	2	6.86	5.57	0.00	f	f	\N	t
1940	134	378	1	3.64	0.00	0.00	f	f	\N	t
1941	134	371	2	3.41	0.00	0.00	f	f	\N	t
1942	134	407	1	2.22	0.00	0.00	f	f	\N	t
1943	134	395	2	3.66	0.00	0.00	f	f	\N	t
1944	134	419	2	5.54	0.00	0.00	f	f	\N	t
1945	134	403	0	0.00	0.00	0.00	f	f	\N	t
1946	134	366	0	0.00	0.00	0.00	f	f	\N	t
1947	134	380	2	3.34	0.00	0.00	f	f	\N	t
1948	134	417	0	0.00	0.00	0.00	f	f	\N	t
1949	134	411	0	0.00	0.00	0.00	f	f	\N	t
1950	134	373	0	0.00	0.00	0.00	f	f	\N	t
1951	134	398	0	0.00	0.00	0.00	f	f	\N	t
1952	135	407	2	4.45	0.00	0.00	f	f	\N	t
1953	135	400	5	10.33	0.00	0.00	f	f	\N	t
1954	135	364	5	12.18	0.00	0.00	f	f	\N	t
1955	135	370	1	2.58	0.00	0.00	f	f	\N	t
1956	135	366	2	8.23	0.00	0.00	f	f	\N	t
1957	135	380	1	2.87	0.00	0.00	f	f	\N	t
1958	135	382	3	4.53	0.00	0.00	f	f	\N	t
1959	135	383	1	1.52	0.00	0.00	f	f	\N	t
1960	135	378	1	1.38	0.00	0.00	f	f	\N	t
1961	135	371	0	0.00	0.00	0.00	f	f	\N	t
1962	135	417	0	0.00	0.00	0.00	f	f	\N	t
1963	135	387	0	0.00	0.00	0.00	f	f	\N	t
1964	135	373	0	0	0	0	f	t	\N	t
1965	135	395	0	0	0	0	f	t	\N	t
1966	135	411	0	0	0	0	f	t	\N	t
1967	135	385	0	0.00	0.00	0.00	f	f	\N	t
1968	136	364	5	15.05	0.00	0.00	f	f	\N	t
1969	136	385	5	8.94	0.00	0.00	f	f	\N	t
1970	136	378	1	1.88	0.00	0.00	f	f	\N	t
1971	136	371	5	19.80	6.87	0.00	f	f	\N	t
1972	136	392	5	8.86	0.00	0.00	f	f	\N	t
1973	136	409	5	10.63	0.00	0.00	f	f	\N	t
1974	136	391	5	15.41	0.00	0.00	f	f	\N	t
1975	136	407	4	6.95	0.00	0.00	f	f	\N	t
1976	136	395	5	6.90	0.00	0.00	f	f	\N	t
1977	136	383	5	8.57	0.00	0.00	f	f	\N	t
1978	136	417	2	3.65	0.00	0.00	f	f	\N	t
1979	136	408	1	1.03	0.00	0.00	f	f	\N	t
1980	136	419	0	0.00	0.00	0.00	f	f	\N	t
1981	136	382	0	0	0	0	f	t	\N	t
1982	136	373	0	0	0	0	f	t	\N	t
1983	136	400	0	0	0	0	f	t	\N	t
1984	136	366	5	8.05	0.00	0.00	f	f	\N	t
1985	136	380	5	8.63	0.00	0.00	f	f	\N	t
1986	137	366	5	11.98	6.71	0.00	f	f	\N	t
1987	137	380	5	7.42	0.00	0.00	f	f	\N	t
1988	137	378	4	5.74	0.00	0.00	f	f	\N	t
1989	137	371	5	12.33	0.00	0.00	f	f	\N	t
1990	137	364	5	9.77	0.00	0.00	f	f	\N	t
1991	137	385	5	7.27	0.00	0.00	f	f	\N	t
1992	137	400	5	10.01	0.00	0.00	f	f	\N	t
1993	137	396	5	6.27	0.00	0.00	f	f	\N	t
1994	137	407	5	7.52	0.00	0.00	f	f	\N	t
1995	137	395	5	8.55	0.00	0.00	f	f	\N	t
1996	137	417	4	6.64	0.00	0.00	f	f	\N	t
1997	137	409	5	9.23	0.00	0.00	f	f	\N	t
1998	137	391	5	14.08	0.00	0.00	f	f	\N	t
1999	137	405	5	6.37	0.00	0.00	f	f	\N	t
2000	137	420	5	7.21	0.00	0.00	f	f	\N	t
2002	137	382	3	3.62	0.00	0.00	f	f	\N	t
2003	137	383	2	2.28	0.00	0.00	f	f	\N	t
2004	137	373	0	0	0	0	f	t	\N	t
2035	139	378	1	0.70	0.00	0.00	f	f	\N	t
2036	139	371	0	0.00	0.00	0.00	f	f	\N	t
2037	140	364	5	8.65	0.00	0.00	f	f	\N	t
2038	140	385	5	6.82	0.00	0.00	f	f	\N	t
2005	137	386	5	8.63	0.00	0.00	f	f	\N	t
2006	138	385	0	0	0	0	f	t	\N	t
2007	138	366	0	0	0	0	f	t	\N	t
2008	138	373	0	0	0	0	f	t	\N	t
2009	138	364	5	15.01	0	0.00	f	f	\N	t
2010	138	380	5	19.49	6.83	0.00	f	f	\N	t
2011	138	378	5	13.76	0.00	0.00	f	f	\N	t
2012	138	371	5	12.98	0.00	0.00	f	f	\N	t
2013	138	407	4	11.46	0.00	0.00	f	f	\N	t
2014	138	395	5	11.87	0.00	0.00	f	f	\N	t
2015	138	417	0	0.00	0.00	0.00	f	f	\N	t
2016	138	387	0	0.00	0.00	0.00	f	f	\N	f
2017	138	420	4	10.24	0.00	0.00	f	f	\N	t
2018	138	405	3	9.22	0.00	0.00	f	f	\N	t
2019	138	382	3	5.37	0.00	0.00	f	f	\N	t
2020	138	383	4	13.30	0.00	0.00	f	f	\N	t
2021	138	400	4	6.64	0.00	0.00	f	f	\N	t
2022	138	381	5	11.58	0.00	0.00	f	f	\N	f
2023	139	364	5	11.68	0.00	0.00	f	f	\N	t
2024	139	385	3	6.61	0.00	0.00	f	f	\N	t
2025	139	407	3	7.31	0.00	0.00	f	f	\N	t
2026	139	395	5	8.34	0.00	0.00	f	f	\N	t
2027	139	366	2	2.53	0.00	0.00	f	f	\N	t
2028	139	380	5	9.40	0.00	0.00	f	f	\N	t
2029	139	382	2	7.26	5.91	0.00	f	f	\N	t
2030	139	383	2	3.01	0.00	0.00	f	f	\N	t
2031	139	417	1	1.08	0.00	0.00	f	f	\N	t
2032	139	408	2	3.87	0.00	0.00	f	f	\N	t
2033	139	420	1	1.73	0.00	0.00	f	f	\N	t
2034	139	405	1	1.33	0.00	0.00	f	f	\N	t
2039	140	392	4	6.56	0.00	0.00	f	f	\N	t
2040	140	393	4	7.97	0.00	0.00	f	f	\N	t
2041	140	409	3	5.60	0.00	0.00	f	f	\N	t
2042	140	411	2	2.98	0.00	0.00	f	f	\N	t
2043	140	407	2	3.67	0.00	0.00	f	f	\N	t
2044	140	395	3	4.82	0.00	0.00	f	f	\N	t
2045	140	366	0	0.00	0.00	0.00	f	f	\N	t
2046	140	380	2	3.87	0.00	0.00	f	f	\N	t
2047	140	383	1	1.28	0.00	0.00	f	f	\N	t
2048	140	371	0	0	0	0	f	t	\N	t
2049	140	382	0	0	0	0	f	t	\N	t
2050	141	382	0	0	0	0	f	t	\N	t
2051	141	378	5	13.22	0.00	0.00	f	f	\N	t
2052	141	371	2	7.17	0.00	0.00	f	f	\N	t
2057	141	364	4	8.45	0.00	0.00	f	f	\N	t
2058	141	385	0	0.00	0.00	0.00	f	f	\N	t
2059	141	410	3	5.48	0.00	0.00	f	f	\N	t
2060	141	413	2	2.83	0.00	0.00	f	f	\N	t
2061	141	407	2	4.29	0.00	0.00	f	f	\N	t
2062	141	395	1	2.31	0.00	0.00	f	f	\N	t
2063	141	366	0	0.00	0.00	0.00	f	f	\N	t
2064	141	380	1	2.29	0.00	0.00	f	f	\N	t
2065	141	383	0	0.00	0.00	0.00	f	f	\N	t
2066	141	417	0	0.00	0.00	0.00	f	f	\N	t
2067	141	400	0	0.00	0.00	0.00	f	f	\N	t
2068	141	396	0	0.00	0.00	0.00	f	f	\N	t
2055	141	392	5	11.28	0	0	f	f	\N	t
2056	141	414	3	3.61	0	0	f	f	\N	t
2053	141	409	5	14.43	6.92	0	f	f	\N	t
2054	141	393	2	3.42	0	0	f	f	\N	t
2069	142	366	0	0	0	0	f	t	\N	t
2070	142	364	5	9.12	0.00	0.00	f	f	\N	t
2071	142	385	3	8.13	0.00	0.00	f	f	\N	t
2072	142	405	5	10.29	0.00	0.00	f	f	\N	t
2073	142	380	2	5.58	0.00	0.00	f	f	\N	t
2074	142	407	0	0.00	0.00	0.00	f	f	\N	t
2075	142	395	3	9.11	0.00	0.00	f	f	\N	t
2076	142	378	2	3.60	0.00	0.00	f	f	\N	t
2077	142	371	2	3.29	0.00	0.00	f	f	\N	t
2078	142	417	1	2.16	0.00	0.00	f	f	\N	t
2079	142	365	1	1.82	0.00	0.00	f	f	\N	t
2080	142	382	1	1.33	0.00	0.00	f	f	\N	t
2081	142	383	0	0.00	0.00	0.00	f	f	\N	t
2082	142	411	0	0.00	0.00	0.00	f	f	\N	t
2083	142	375	0	0.00	0.00	0.00	f	f	\N	t
2084	143	382	0	0	0	0	f	t	\N	t
2085	143	364	0	0	0	0	f	t	\N	t
2086	143	385	0	0	0	0	f	t	\N	t
2087	143	366	0	0	0	0	f	t	\N	t
2088	143	380	0	0	0	0	f	t	\N	t
2089	143	383	0	0	0	0	f	t	\N	t
2090	143	407	5	11.95	0.00	0.00	f	f	\N	t
2091	143	395	5	9.91	0.00	0.00	f	f	\N	t
2092	143	378	4	11.84	0.00	0.00	f	f	\N	t
2093	143	371	3	4.49	0.00	0.00	f	f	\N	t
2094	143	400	4	8.12	0.00	0.00	f	f	\N	t
2095	143	396	1	2.33	0.00	0.00	f	f	\N	t
2096	143	392	2	3.33	0.00	0.00	f	f	\N	t
2097	143	393	2	4.05	0.00	0.00	f	f	\N	t
2098	143	386	2	3.64	0.00	0.00	f	f	\N	t
2099	143	418	3	3.64	0.00	0.00	f	f	\N	t
2100	143	405	2	3.54	0.00	0.00	f	f	\N	t
2101	143	420	2	3.24	0.00	0.00	f	f	\N	t
2102	143	417	0	0.00	0.00	0.00	f	f	\N	t
2103	143	411	0	0.00	0.00	0.00	f	f	\N	t
2104	144	364	5	12.42	0.00	0.00	f	f	\N	t
2105	144	385	5	9.44	0.00	0.00	f	f	\N	t
2106	144	417	5	11.80	0.00	0.00	f	f	\N	t
2107	144	365	5	7.26	0.00	0.00	f	f	\N	t
2108	144	409	5	8.58	0.00	0.00	f	f	\N	t
2109	144	372	5	9.90	0.00	0.00	f	f	\N	t
2110	144	420	5	8.95	0.00	0.00	f	f	\N	t
2111	144	405	5	8.31	0.00	0.00	f	f	\N	t
2112	144	407	5	6.70	0.00	0.00	f	f	\N	t
2113	144	395	5	10.36	0.00	0.00	f	f	\N	t
2114	144	366	5	9.86	0.00	0.00	f	f	\N	t
2115	144	380	5	7.14	0.00	0.00	f	f	\N	t
2116	144	404	4	3.87	0.00	0.00	f	f	\N	t
2117	144	369	5	11.08	0.00	0.00	f	f	\N	t
2118	144	400	5	5.36	0.00	0.00	f	f	\N	t
2119	144	396	5	6.54	0.00	0.00	f	f	\N	t
2120	144	411	3	7.08	0.00	0.00	f	f	\N	t
2121	144	393	3	4.74	0.00	0.00	f	f	\N	t
2122	144	391	4	11.77	0.00	0.00	f	f	\N	t
2123	144	382	4	7.42	0.00	0.00	f	f	\N	t
2124	144	383	3	2.84	0.00	0.00	f	f	\N	t
2125	144	378	4	5.66	0.00	0.00	f	f	\N	t
2126	144	371	3	4.53	0.00	0.00	f	f	\N	t
2127	145	364	4	8.98	0.00	0.00	f	f	\N	t
2128	145	385	3	7.35	0.00	0.00	f	f	\N	t
2129	145	366	3	9.23	0.00	0.00	f	f	\N	t
2130	145	368	2	2.43	0.00	0.00	f	f	\N	t
2131	145	386	3	5.90	0.00	0.00	f	f	\N	t
2132	145	418	0	0.00	0.00	0.00	f	f	\N	t
2133	145	420	3	3.86	0.00	0.00	f	f	\N	t
2134	145	407	2	3.74	0.00	0.00	f	f	\N	t
2135	145	395	0	0.00	0.00	0.00	f	f	\N	t
2136	145	382	0	0.00	0.00	0.00	f	f	\N	t
2137	145	383	2	1.60	0.00	0.00	f	f	\N	t
2138	145	411	0	0.00	0.00	0.00	f	f	\N	t
2139	145	375	0	0.00	0.00	0.00	f	f	\N	t
2140	145	417	0	0.00	0.00	0.00	f	f	\N	t
2141	145	365	0	0.00	0.00	0.00	f	f	\N	t
2142	145	371	0	0	0	0	f	t	\N	t
2143	145	380	0	0	0	0	f	t	\N	t
2144	165	378	4	11.30	5.65	0.00	f	f	\N	t
2145	165	371	5	8.62	0.00	0.00	f	f	\N	t
2146	165	386	5	10.54	0.00	0.00	f	f	\N	t
2147	165	418	2	3.57	0.00	0.00	f	f	\N	t
2148	165	385	4	9.24	0.00	0.00	f	f	\N	t
2149	165	366	2	4.53	0.00	0.00	f	f	\N	t
2150	165	382	1	1.99	0.00	0.00	f	f	\N	t
2151	165	383	2	5.30	0.00	0.00	f	f	\N	t
2152	165	407	1	1.89	0.00	0.00	f	f	\N	t
2153	165	395	2	3.79	0.00	0.00	f	f	\N	t
2154	165	364	0	0	0	0	f	t	\N	t
2155	164	364	0	0	0	0	f	t	\N	t
2157	164	395	0	0	0	0	f	t	\N	t
2158	164	407	0	0	0	0	f	t	\N	t
2156	164	391	0	0	0	0	f	t	\N	t
2159	164	386	3	7.07	0.00	0.00	f	f	\N	t
2160	164	418	3	4.74	0.00	0.00	f	f	\N	t
2161	164	382	3	6.45	0.00	0.00	f	f	\N	t
2162	164	383	3	5.24	0.00	0.00	f	f	\N	t
2163	164	417	1	1.41	0.00	0.00	f	f	\N	t
2164	164	387	3	5.69	0.00	0.00	f	f	\N	f
2165	164	411	2	2.06	0.00	0.00	f	f	\N	t
2166	164	375	2	3.39	0.00	0.00	f	f	\N	t
2167	164	385	0	0.00	0.00	0.00	f	f	\N	t
2168	164	366	0	0.00	0.00	0.00	f	f	\N	t
2169	164	378	1	2.50	0.00	0.00	f	f	\N	t
2170	164	371	1	0.89	0.00	0.00	f	f	\N	t
2171	163	386	5	8.70	0.00	0.00	f	f	\N	t
2172	163	418	4	6.84	0.00	0.00	f	f	\N	t
2173	163	407	5	8.51	0.00	0.00	f	f	\N	t
2174	163	395	3	6.72	0.00	0.00	f	f	\N	t
2175	163	417	0	0.00	0.00	0.00	f	f	\N	t
2176	163	365	2	8.42	6.82	0.00	f	f	\N	f
2177	163	385	4	3.97	0.00	0.00	f	f	\N	t
2178	163	366	0	0.00	0.00	0.00	f	f	\N	t
2179	163	411	0	0.00	0.00	0.00	f	f	\N	t
2180	163	375	0	0.00	0.00	0.00	f	f	\N	t
2181	163	378	0	0	0	0	f	t	\N	t
2182	163	364	0	0	0	0	f	t	\N	t
2183	163	382	0	0	0	0	f	t	\N	t
2184	163	371	0	0	0	0	f	t	\N	t
2185	163	391	0	0	0	0	f	t	\N	t
2186	162	385	5	11.90	0.00	0.00	f	f	\N	t
2187	162	366	5	15.00	5.56	0.00	f	f	\N	t
2188	162	392	4	5.59	0.00	0.00	f	f	\N	t
2189	162	409	5	13.85	0.00	0.00	f	f	\N	t
2190	162	407	4	5.78	0.00	0.00	f	f	\N	t
2191	162	395	5	10.08	0.00	0.00	f	f	\N	t
2192	162	417	4	5.73	0.00	0.00	f	f	\N	t
2193	162	365	5	8.21	0.00	0.00	f	f	\N	f
2194	162	393	0	0.00	0.00	0.00	f	f	\N	t
2195	162	411	0	0.00	0.00	0.00	f	f	\N	t
2196	162	391	0	0	0	0	f	t	\N	t
2197	162	364	0	0	0	0	f	t	\N	t
2198	162	378	0	0	0	0	f	t	\N	t
2199	162	371	0	0	0	0	f	t	\N	t
2200	162	382	0	0	0	0	f	t	\N	t
2201	161	385	5	9.99	0.00	0.00	f	f	\N	t
2202	161	366	5	23.96	8.33	0.00	f	f	\N	t
2203	161	364	5	15.88	0.00	0.00	f	f	\N	t
2204	161	391	5	10.97	0.00	0.00	f	f	\N	t
2205	161	382	3	10.58	0.00	0.00	f	f	\N	t
2206	161	383	4	7.78	0.00	0.00	f	f	\N	t
2207	161	378	5	11.23	0.00	0.00	f	f	\N	t
2208	161	371	3	5.39	0.00	0.00	f	f	\N	t
2209	161	407	1	1.60	0.00	0.00	f	f	\N	t
2210	161	395	5	10.60	0.00	0.00	f	f	\N	t
2211	160	364	5	14.60	0.00	0.00	f	f	\N	t
2212	160	391	5	15.69	7.21	0.00	f	f	\N	t
2213	160	407	5	9.50	0.00	0.00	f	f	\N	t
2214	160	395	5	15.03	0.00	0.00	f	f	\N	t
2215	160	372	5	11.73	0.00	0.00	f	f	\N	t
2216	160	409	5	12.34	0.00	0.00	f	f	\N	t
2217	160	392	5	12.37	0.00	0.00	f	f	\N	t
2218	160	384	5	11.59	0.00	0.00	f	f	\N	f
2219	160	417	5	9.32	0.00	0.00	f	f	\N	t
2220	160	408	5	12.63	0.00	0.00	f	f	\N	t
2221	160	386	5	13.40	0.00	0.00	f	f	\N	t
2222	160	418	5	8.15	0.00	0.00	f	f	\N	t
2223	160	378	5	12.19	0.00	0.00	f	f	\N	t
2224	160	371	5	8.04	0.00	0.00	f	f	\N	t
2225	160	385	5	10.31	0.00	0.00	f	f	\N	t
2226	160	366	5	9.01	0.00	0.00	f	f	\N	t
2227	160	411	5	7.20	0.00	0.00	f	f	\N	t
2228	160	375	3	4.58	0.00	0.00	f	f	\N	t
2229	159	407	4	8.57	0.00	0.00	f	f	\N	t
2230	159	395	5	25.81	9.35	0.00	f	f	\N	t
2231	159	364	2	3.79	0.00	0.00	f	f	\N	t
2232	159	391	3	8.28	0.00	0.00	f	f	\N	t
2233	159	385	1	1.72	0.00	0.00	f	f	\N	t
2234	159	366	2	5.13	0.00	0.00	f	f	\N	t
2235	159	386	1	3.59	0.00	0.00	f	f	\N	t
2236	159	418	1	1.63	0.00	0.00	f	f	\N	t
2237	159	382	1	2.93	0.00	0.00	f	f	\N	t
2238	159	383	0	0.00	0.00	0.00	f	f	\N	t
2239	159	417	0	0.00	0.00	0.00	f	f	\N	t
2240	159	408	0	0.00	0.00	0.00	f	f	\N	t
2241	159	378	0	0	0	0	f	t	\N	t
2242	159	371	0	0	0	0	f	t	\N	t
2243	158	364	5	12.00	0.00	0.00	f	f	\N	t
2244	158	391	5	12.75	0.00	0.00	f	f	\N	t
2245	158	386	5	16	0.00	0.00	f	f	\N	t
2246	158	418	4	8.50	0.00	0.00	f	f	\N	t
2247	158	385	5	14.25	0.00	0.00	f	f	\N	t
2248	158	366	5	10.13	0.00	0.00	f	f	\N	t
2249	158	407	3	8.25	0.00	0.00	f	f	\N	t
2250	158	395	4	15.00	0.00	0.00	f	f	\N	t
2251	158	382	5	12.50	0.00	0.00	f	f	\N	t
2252	158	383	3	6.75	0.00	0.00	f	f	\N	t
2253	158	411	5	10.75	0.00	0.00	f	f	\N	t
2254	158	393	3	4.50	0.00	0.00	f	f	\N	t
2255	158	378	0	0	0	0	f	t	\N	t
2256	158	371	0	0	0	0	f	t	\N	t
2257	157	366	0	0	0	0	f	t	\N	t
2258	157	364	5	13.23	0.00	0.00	f	f	\N	t
2259	157	391	5	11.27	0.00	0.00	f	f	\N	t
2260	157	386	5	12.82	0.00	0.00	f	f	\N	t
2261	157	418	3	6.15	0.00	0.00	f	f	\N	t
2262	157	378	3	6.96	0.00	0.00	f	f	\N	t
2263	157	371	3	3.96	0.00	0.00	f	f	\N	t
2264	157	407	0	0.00	0.00	0.00	f	f	\N	t
2265	157	395	1	4.97	0.00	0.00	f	f	\N	t
2266	157	417	0	0.00	0.00	0.00	f	f	\N	t
2267	157	393	3	4.61	0.00	0.00	f	f	\N	t
2268	157	385	0	0.00	0.00	0.00	f	f	\N	t
2269	157	382	0	0.00	0.00	0.00	f	f	\N	t
2270	157	383	0	0.00	0.00	0.00	f	f	\N	t
2273	156	385	3	6.51	0.00	0.00	f	f	\N	t
2274	156	366	5	12.72	0.00	0.00	f	f	\N	t
2275	156	378	4	7.49	0.00	0.00	f	f	\N	t
2276	156	371	2	3.79	0.00	0.00	f	f	\N	t
2277	156	386	4	8.81	0.00	0.00	f	f	\N	t
2278	156	418	1	1.21	0.00	0.00	f	f	\N	t
2279	156	382	2	4.39	0.00	0.00	f	f	\N	t
2280	156	383	1	3.56	0.00	0.00	f	f	\N	t
2281	156	417	2	2.79	0.00	0.00	f	f	\N	t
2282	156	365	3	5.00	0.00	0.00	f	f	\N	t
2283	156	407	1	2.02	0.00	0.00	f	f	\N	t
2284	156	395	2	5.01	0.00	0.00	f	f	\N	t
2271	156	364	5	16.66	7.51	0	f	f	\N	t
2272	156	391	5	7.61	0	0	f	f	\N	t
2285	155	407	2	3.15	0.00	0.00	f	f	\N	t
2286	155	395	5	9.86	0.00	0.00	f	f	\N	t
2287	155	378	2	2.95	0.00	0.00	f	f	\N	t
2288	155	371	2	6.03	0.00	0.00	f	f	\N	t
2289	155	386	2	5.20	0.00	0.00	f	f	\N	t
2290	155	418	1	3.09	0.00	0.00	f	f	\N	t
2291	155	385	3	4.09	0.00	0.00	f	f	\N	t
2292	155	366	1	2.98	0.00	0.00	f	f	\N	t
2293	155	417	0	0.00	0.00	0.00	f	f	\N	t
2294	155	365	3	6.38	0.00	0.00	f	f	\N	t
2295	155	364	1	1.62	0.00	0.00	f	f	\N	t
2296	155	391	0	0.00	0.00	0.00	f	f	\N	t
2297	155	382	0	0	0	0	f	t	\N	t
2298	154	386	4	6.89	0.00	0.00	f	f	\N	t
2299	154	418	1	2.33	0.00	0.00	f	f	\N	t
2300	154	385	2	2.91	0.00	0.00	f	f	\N	t
2301	154	366	0	0.00	0.00	0.00	f	f	\N	t
2302	154	378	1	1.26	0.00	0.00	f	f	\N	t
2303	154	371	1	1.31	0.00	0.00	f	f	\N	t
2304	154	407	1	1.24	0.00	0.00	f	f	\N	t
2305	154	395	1	1.25	0.00	0.00	f	f	\N	t
2306	154	411	0	0.00	0.00	0.00	f	f	\N	t
2307	154	393	0	0.00	0.00	0.00	f	f	\N	t
2308	154	364	0	0	0	0	f	t	\N	t
2309	154	382	0	0	0	0	f	t	\N	t
2310	153	364	1	1.27	0.00	0.00	f	f	\N	t
2311	153	397	3	7.15	0.00	0.00	f	f	\N	t
2312	153	386	1	3.30	0.00	0.00	f	f	\N	t
2313	153	418	3	4.87	0.00	0.00	f	f	\N	t
2314	153	378	0	0.00	0.00	0.00	f	f	\N	t
2315	153	371	3	6.56	0.00	0.00	f	f	\N	t
2316	153	404	1	2.69	0.00	0.00	f	f	\N	t
2317	153	382	0	0.00	0.00	0.00	f	f	\N	t
2318	153	366	0	0	0	0	f	t	\N	t
2319	153	385	0	0	0	0	f	t	\N	t
2320	153	395	0	0	0	0	f	t	\N	t
2321	152	364	1	1.27	0.00	0.00	f	f	\N	t
2322	152	397	3	7.15	0.00	0.00	f	f	\N	t
2323	152	386	1	3.30	0.00	0.00	f	f	\N	t
2324	152	418	3	4.87	0.00	0.00	f	f	\N	t
2325	152	378	0	0.00	0.00	0.00	f	f	\N	t
2326	152	371	3	6.56	0.00	0.00	f	f	\N	t
2327	152	404	1	2.69	0.00	0.00	f	f	\N	t
2328	152	382	0	0.00	0.00	0.00	f	f	\N	t
2329	152	366	0	0	0	0	f	t	\N	t
2330	152	385	0	0	0	0	f	t	\N	t
2331	152	395	0	0	0	0	f	t	\N	t
2332	151	364	5	16.56	0.00	0.00	f	f	\N	t
2333	151	397	2	3.38	0.00	0.00	f	f	\N	t
2334	151	378	5	8.11	0.00	0.00	f	f	\N	t
2335	151	371	4	5.52	0.00	0.00	f	f	\N	t
2336	151	417	5	9.17	0.00	0.00	f	f	\N	t
2337	151	395	3	3.51	0.00	0.00	f	f	\N	t
2338	151	404	4	3.91	0.00	0.00	f	f	\N	t
2339	151	369	5	6.58	0.00	0.00	f	f	\N	t
2340	151	411	4	7.47	0.00	0.00	f	f	\N	t
2341	151	375	1	2.72	0.00	0.00	f	f	\N	t
2342	151	385	0	0.00	0.00	0.00	f	f	\N	t
2343	151	366	5	7.37	0.00	0.00	f	f	\N	t
2344	151	386	1	2.44	0.00	0.00	f	f	\N	t
2345	151	418	1	3.09	0.00	0.00	f	f	\N	t
2346	151	382	0	0.00	0.00	0.00	f	f	\N	t
2347	151	383	2	3.99	0.00	0.00	f	f	\N	t
2348	151	373	0	0	0	0	f	t	\N	t
2349	150	364	5	9.35	0.00	0.00	f	f	\N	t
2350	150	397	5	7.18	0.00	0.00	f	f	\N	t
2351	150	407	2	2.66	0.00	0.00	f	f	\N	t
2352	150	395	5	10.42	0.00	0.00	f	f	\N	t
2353	150	386	4	7.83	0.00	0.00	f	f	\N	t
2354	150	418	2	3.61	0.00	0.00	f	f	\N	t
2355	150	417	2	3.74	0.00	0.00	f	f	\N	t
2356	150	388	5	7.54	0.00	0.00	f	f	\N	t
2357	150	385	5	7.09	0.00	0.00	f	f	\N	t
2358	150	366	4	4.17	0.00	0.00	f	f	\N	t
2359	150	378	1	1.36	0.00	0.00	f	f	\N	t
2360	150	371	2	1.87	0.00	0.00	f	f	\N	t
2361	150	382	0	0	0	0	f	t	\N	t
2362	150	383	0	0	0	0	f	t	\N	t
2363	150	373	0	0	0	0	f	t	\N	t
2364	149	407	5	14.72	0.00	0.00	f	f	\N	t
2365	149	395	5	9.68	0.00	0.00	f	f	\N	t
2366	149	386	5	16.12	7.56	0.00	f	f	\N	t
2367	149	418	3	4.52	0.00	0.00	f	f	\N	t
2368	149	382	4	7.96	0.00	0.00	f	f	\N	t
2369	149	383	3	6.90	0.00	0.00	f	f	\N	t
2370	149	364	5	11.31	0.00	0.00	f	f	\N	t
2371	149	397	1	2.01	0.00	0.00	f	f	\N	t
2372	149	417	0	0.00	0.00	0.00	f	f	\N	t
2373	149	365	3	13.27	0.00	0.00	f	f	\N	t
2374	149	385	2	6.03	0.00	0.00	f	f	\N	t
2375	149	366	2	3.08	0.00	0.00	f	f	\N	t
2376	149	378	3	3.92	0.00	0.00	f	f	\N	t
2377	149	411	0	0.00	0.00	0.00	f	f	\N	t
2378	149	393	0	0.00	0.00	0.00	f	f	\N	t
2379	149	373	0	0	0	0	f	t	\N	t
2380	149	371	0	0	0	0	f	t	\N	t
2381	148	364	5	12.50	0.00	0.00	f	f	\N	t
2382	148	397	5	12.53	0.00	0.00	f	f	\N	t
2383	148	385	5	13.16	0.00	0.00	f	f	\N	t
2384	148	366	5	10.36	0.00	0.00	f	f	\N	t
2385	148	386	5	10.21	0.00	0.00	f	f	\N	t
2386	148	418	5	12.21	0.00	0.00	f	f	\N	t
2387	148	407	5	8.41	0.00	0.00	f	f	\N	t
2388	148	395	5	10.88	0.00	0.00	f	f	\N	t
2389	148	409	5	9.07	0.00	0.00	f	f	\N	t
2390	148	372	5	9.42	0.00	0.00	f	f	\N	t
2391	148	378	5	8.45	0.00	0.00	f	f	\N	t
2392	148	371	5	6.94	0.00	0.00	f	f	\N	t
2393	148	417	5	7.67	0.00	0.00	f	f	\N	t
2394	148	365	5	6.88	0.00	0.00	f	f	\N	t
2395	148	420	5	6.78	0.00	0.00	f	f	\N	t
2396	148	390	5	6.85	0.00	0.00	f	f	\N	t
2397	148	405	0	0.00	0.00	0.00	t	f	\N	t
2398	148	411	0	0.00	0.00	0.00	t	f	\N	t
2399	148	393	0	0.00	0.00	0.00	t	f	\N	t
2400	148	382	0	0	0	0	f	t	\N	t
2401	148	373	0	0	0	0	f	t	\N	t
2402	148	380	0	0	0	0	f	t	\N	t
2403	147	378	5	15.23	0.00	0.00	f	f	\N	t
2404	147	371	5	11.21	0.00	0.00	f	f	\N	t
2405	147	364	5	12.96	0.00	0.00	f	f	\N	t
2406	147	397	5	8.32	0.00	0.00	f	f	\N	t
2407	147	393	5	9.78	0.00	0.00	f	f	\N	t
2408	147	411	4	7.09	0.00	0.00	f	f	\N	t
2409	147	405	5	8.18	0.00	0.00	f	f	\N	t
2410	147	380	5	7.80	0.00	0.00	f	f	\N	t
2411	147	382	5	7.72	0.00	0.00	f	f	\N	t
2412	147	395	5	8.26	0.00	0.00	f	f	\N	t
2413	147	417	3	5.15	0.00	0.00	f	f	\N	t
2414	147	365	5	9.62	0.00	0.00	f	f	\N	t
2415	147	420	5	7.81	0.00	0.00	f	f	\N	t
2416	147	390	5	5.55	0.00	0.00	f	f	\N	t
2417	147	391	5	10.28	0.00	0.00	f	f	\N	t
2418	147	415	1	1.67	0.00	0.00	f	f	\N	t
2419	147	400	5	9.00	0.00	0.00	f	f	\N	t
2420	147	396	0	0.00	0.00	0.00	f	f	\N	t
2421	147	386	1	1.46	0.00	0.00	f	f	\N	t
2422	147	418	4	6.43	0.00	0.00	f	f	\N	t
2423	147	373	0	0	0	0	f	t	\N	t
2424	147	383	0	0	0	0	f	t	\N	t
2425	147	407	0	0	0	0	f	t	\N	t
2426	147	385	5	10.22	0.00	0.00	f	f	\N	t
2427	147	366	5	7.71	0.00	0.00	f	f	\N	t
2428	146	407	3	11.98	0.00	0.00	f	f	\N	t
2429	146	395	3	11.09	0.00	0.00	f	f	\N	t
2430	146	364	5	11.36	0.00	0.00	f	f	\N	t
2431	146	397	4	9.04	0.00	0.00	f	f	\N	t
2432	146	385	5	11.23	0.00	0.00	f	f	\N	t
2433	146	366	1	4.45	0.00	0.00	f	f	\N	t
2436	146	417	0	0.00	0.00	0.00	f	f	\N	t
2437	146	365	4	7.20	0.00	0.00	f	f	\N	t
2438	146	391	3	4.90	0.00	0.00	f	f	\N	t
2439	146	415	0	0.00	0.00	0.00	f	f	\N	t
2440	146	405	1	1.61	0.00	0.00	f	f	\N	t
2441	146	380	0	0.00	0.00	0.00	f	f	\N	t
2442	146	386	1	1.33	0.00	0.00	f	f	\N	t
2443	146	418	0	0.00	0.00	0.00	f	f	\N	t
2444	146	410	0	0.00	0.00	0.00	f	f	\N	t
2445	146	421	0	0.00	0.00	0.00	f	f	\N	t
2446	146	382	0	0	0	0	f	t	\N	t
2447	146	373	0	0	0	0	f	t	\N	t
2448	146	383	0	0	0	0	f	t	\N	t
2434	146	378	3	10.35	6.73	0	f	f	\N	t
2435	146	371	2	2.69	0	0	f	f	\N	t
\.


--
-- Data for Name: team_results; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.team_results (id, tournament_id, angler1_id, angler2_id, total_weight, place_finish) FROM stdin;
464	134	364	385	15.09	1
463	134	409	365	11.89	2
465	134	400	396	11.14	3
466	134	382	383	8.36	4
468	134	378	371	7.05	5
467	134	391	\N	6.86	6
469	134	407	395	5.88	7
470	134	419	403	5.54	8
471	134	366	380	3.34	9
472	134	417	411	0	10
473	134	373	398	0	11
495	136	366	380	16.68	4
484	136	364	385	23.99	1
485	136	378	371	21.68	2
486	136	392	409	19.49	3
487	136	391	\N	15.41	5
488	136	407	395	13.85	6
489	136	383	\N	8.57	7
490	136	417	408	4.68	8
491	136	419	\N	0	9
492	136	382	\N	0	10
493	136	373	\N	0	11
494	136	400	\N	0	12
511	137	386	\N	8.63	9
506	137	373	\N	0	11
496	137	366	380	19.40	1
497	137	378	371	18.07	2
498	137	364	385	17.04	3
499	137	400	396	16.28	4
500	137	407	395	16.07	5
501	137	417	409	15.87	6
502	137	391	\N	14.08	7
503	137	405	420	13.58	8
505	137	382	383	5.90	10
521	138	400	381	18.22	6
512	138	385	\N	0	10
513	138	366	\N	0	8
514	138	373	\N	0	7
515	138	364	380	34.50	1
516	138	378	371	26.74	2
517	138	407	395	23.33	3
518	138	417	387	0	9
519	138	420	405	19.46	4
520	138	382	383	18.67	5
474	135	407	400	14.78	1
475	135	364	370	14.76	2
476	135	366	380	11.10	3
477	135	382	383	6.05	4
478	135	378	371	1.38	5
479	135	417	387	0	6
480	135	373	\N	0	6
481	135	395	\N	0	6
482	135	411	\N	0	6
483	135	385	\N	0	6
534	140	383	\N	1.28	6
529	140	364	385	15.47	1
530	140	392	393	14.53	2
531	140	409	411	8.58	3
532	140	407	395	8.49	4
533	140	366	380	3.87	5
535	140	371	\N	0	7
536	140	382	\N	0	7
522	139	364	385	18.29	1
523	139	407	395	15.65	2
524	139	366	380	11.93	3
525	139	382	383	10.27	4
526	139	417	408	4.95	5
527	139	420	405	3.06	6
528	139	378	371	0.70	7
566	143	405	420	6.78	6
563	143	400	396	10.45	3
555	143	382	\N	0	7
556	143	364	\N	0	7
557	143	385	\N	0	7
547	142	366	\N	0	7
548	142	364	385	17.25	1
549	142	405	380	15.87	2
550	142	407	395	9.11	3
551	142	378	371	6.89	4
552	142	417	365	3.98	5
553	142	382	383	1.33	6
554	142	411	375	0	7
537	141	382	\N	0	8
538	141	378	371	20.39	1
541	141	364	385	8.45	4
542	141	410	413	8.31	5
543	141	407	395	6.60	6
544	141	366	380	2.29	7
545	141	383	417	0	8
546	141	400	396	0	8
540	141	392	414	14.89	3
539	141	409	393	17.85	2
558	143	366	\N	0	7
559	143	380	\N	0	7
560	143	383	\N	0	7
561	143	407	395	21.86	1
562	143	378	371	16.33	2
564	143	392	393	7.38	4
565	143	386	418	7.28	5
567	143	417	411	0	7
588	145	371	\N	0	7
578	144	382	383	10.26	11
576	144	411	393	11.82	9
574	144	404	369	14.95	7
568	144	364	385	21.86	1
569	144	417	365	19.06	2
570	144	409	372	18.48	3
571	144	420	405	17.26	4
572	144	407	395	17.06	5
573	144	366	380	17.00	6
575	144	400	396	11.90	8
577	144	391	\N	11.77	10
579	144	378	371	10.19	12
589	145	380	\N	0	7
587	145	417	365	0	7
585	145	382	383	1.60	6
586	145	411	375	0	7
583	145	420	\N	3.86	4
580	145	364	385	16.33	1
595	165	364	\N	0	6
581	145	366	368	11.66	2
582	145	386	418	5.90	3
584	145	407	395	3.74	5
593	165	382	383	7.29	4
594	165	407	395	5.68	5
592	165	385	366	13.77	3
590	165	378	371	19.92	1
591	165	386	418	14.11	2
599	164	407	\N	0	6
598	164	395	\N	0	6
618	162	407	395	15.86	3
742	147	378	371	26.44	1
639	160	411	375	11.78	9
631	160	364	391	30.29	1
632	160	407	395	24.53	2
633	160	372	409	24.07	3
634	160	392	384	23.96	4
635	160	417	408	21.95	5
636	160	386	418	21.55	6
637	160	378	371	20.23	7
638	160	385	366	19.32	8
655	158	371	\N	0	7
648	158	364	391	24.75	1
649	158	386	418	24.50	2
650	158	385	366	24.38	3
651	158	407	395	23.25	4
652	158	382	383	19.25	5
596	164	364	\N	0	6
597	164	391	\N	0	6
600	164	386	418	11.81	1
601	164	382	383	11.69	2
602	164	417	387	7.10	3
603	164	411	375	5.45	4
604	164	385	366	0	6
605	164	378	371	3.39	5
653	158	411	393	15.25	6
654	158	378	\N	0	7
677	155	382	\N	0	7
671	155	407	395	13.01	1
672	155	378	371	8.98	2
616	162	385	366	26.90	1
617	162	392	409	19.44	2
619	162	417	365	13.94	4
620	162	393	411	0	5
621	162	391	\N	0	5
622	162	364	\N	0	5
623	162	378	\N	0	5
624	162	371	\N	0	5
625	162	382	\N	0	5
673	155	386	418	8.29	3
674	155	385	366	7.07	4
675	155	417	365	6.38	5
676	155	364	391	1.62	6
626	161	385	366	33.95	1
627	161	364	391	26.85	2
628	161	382	383	18.36	3
629	161	378	371	16.62	4
630	161	407	395	12.20	5
606	163	386	418	15.54	1
607	163	407	395	15.23	2
608	163	417	365	8.42	3
609	163	385	366	3.97	4
610	163	411	375	0	5
611	163	378	\N	0	5
612	163	364	\N	0	5
613	163	382	\N	0	5
614	163	371	\N	0	5
615	163	391	\N	0	5
640	159	407	395	34.38	1
641	159	364	391	12.07	2
642	159	385	366	6.85	3
643	159	386	418	5.22	4
644	159	382	383	2.93	5
645	159	417	408	0	6
646	159	378	\N	0	6
647	159	371	\N	0	6
669	156	417	365	7.79	6
665	156	385	366	19.23	2
666	156	378	371	11.28	3
667	156	386	418	10.02	4
668	156	382	383	7.95	5
670	156	407	395	7.03	7
664	156	364	391	24.27	1
700	152	395	\N	0	5
656	157	366	\N	0	6
657	157	364	391	24.50	1
658	157	386	418	18.97	2
659	157	378	371	10.92	3
660	157	407	395	4.97	4
661	157	417	393	4.61	5
662	157	385	\N	0	6
663	157	382	383	0	6
693	152	364	397	8.42	1
694	152	386	418	8.17	2
695	152	378	371	6.56	3
696	152	404	\N	2.69	4
697	152	382	\N	0	5
698	152	366	\N	0	5
699	152	385	\N	0	5
678	154	386	418	9.22	1
679	154	385	366	2.91	2
680	154	378	371	2.57	3
681	154	407	395	2.49	4
682	154	411	393	0	5
683	154	364	\N	0	5
684	154	382	\N	0	5
686	153	386	418	8.17	2
685	153	364	397	8.42	1
687	153	378	371	6.56	3
688	153	404	\N	2.69	4
689	153	382	\N	0	5
690	153	366	\N	0	5
691	153	385	\N	0	5
692	153	395	\N	0	5
708	151	382	383	3.99	8
705	151	411	375	10.19	5
701	151	364	397	19.94	1
702	151	378	371	13.63	2
703	151	417	395	12.68	3
717	150	383	\N	0	7
718	150	373	\N	0	7
715	150	378	371	3.23	6
704	151	404	369	10.49	4
706	151	385	366	7.37	6
707	151	386	418	5.53	7
709	151	373	\N	0	9
710	150	364	397	16.53	1
716	150	382	\N	0	7
711	150	407	395	13.08	2
712	150	386	418	11.44	3
713	150	417	388	11.28	4
714	150	385	366	11.26	5
725	149	378	\N	3.92	7
724	149	385	366	9.11	6
722	149	364	397	13.32	4
723	149	417	365	13.27	5
721	149	382	383	14.86	3
719	149	407	395	24.40	1
746	147	382	395	15.98	5
743	147	364	397	21.28	2
744	147	393	411	16.87	4
720	149	386	418	20.64	2
726	149	411	393	0	8
727	149	373	\N	0	8
728	149	371	\N	0	8
765	146	382	\N	0	9
756	146	407	395	23.07	1
757	146	364	397	20.40	2
758	146	385	366	15.68	3
760	146	417	365	7.20	5
745	147	405	380	15.98	5
747	147	417	365	14.77	7
748	147	420	390	13.36	8
749	147	391	415	11.95	9
750	147	400	396	9.00	10
751	147	386	418	7.89	11
752	147	373	\N	0	12
753	147	383	\N	0	12
754	147	407	\N	0	12
755	147	385	366	17.93	3
761	146	391	415	4.90	6
762	146	405	380	1.61	7
763	146	386	418	1.33	8
764	146	410	421	0	9
766	146	373	\N	0	9
767	146	383	\N	0	9
759	146	378	371	13.04	4
729	148	364	397	25.03	1
730	148	385	366	23.52	2
731	148	386	418	22.42	3
732	148	407	395	19.29	4
733	148	409	372	18.49	5
734	148	378	371	15.39	6
735	148	417	365	14.55	7
736	148	420	390	13.63	8
737	148	405	\N	0	9
738	148	411	393	0	9
739	148	382	\N	0	9
740	148	373	\N	0	9
741	148	380	\N	0	9
\.


--
-- Data for Name: tournaments; Type: TABLE DATA; Schema: public; Owner: sabc_user
--

COPY public.tournaments (id, event_id, poll_id, name, lake_id, ramp_id, lake_name, ramp_name, start_time, end_time, fish_limit, entry_fee, is_team, is_paper, big_bass_carryover, complete, created_by, limit_type, aoy_points) FROM stdin;
131	139	\N	Test Event for AoY	\N	\N	travis	mansfield_dam	06:00:00	15:00:00	5	25.0	t	f	0.0	f	\N	angler	f
132	143	\N	Test AoY Points Working	\N	\N	travis	mansfield_dam	06:00:00	15:00:00	5	25.0	t	f	0.0	f	\N	angler	f
133	144	\N	Final Test Event - Updated	\N	\N	canyon	canyon_park	07:00:00	16:00:00	6	30.0	t	f	0.0	f	\N	angler	t
140	150	\N	July 2023 Tournament	6	12	Lake Austin	loop 360 boat ramp	00:00:00	09:00:00	5	25.0	t	f	0.0	t	\N	angler	t
134	137	\N	January 2023 Tournament	5	9	Lake LBJ	yacht club & marina	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
135	145	\N	February 2025 Tournament	1	1	Lake Belton	cedar ridge park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
141	151	\N	August 2023 Tournament	5	9	Lake LBJ	yacht club & marina	00:00:00	09:00:00	5	25.0	t	f	0.0	t	\N	angler	t
142	152	\N	September 2023 Tournament	10	21	Still House Hollow Lake	riversbend park	07:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
143	153	\N	October 2025 Tournament	14	33	Canyon Lake	canyon lake boat ramp 17	07:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
144	154	\N	November 2023 Tournament	3	7	Lake Travis	tournament point	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
136	146	\N	March 2023 Tournament	9	19	Lake Buchanan	Burnett County Park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
138	148	\N	May 2023 Tournament	10	21	Still House Hollow Lake	riversbend park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
139	149	\N	June 2023 Tournament	9	19	Lake Buchanan	Burnett County Park	05:00:00	13:00:00	5	25.0	t	f	0.0	t	\N	angler	t
145	155	\N	December 2023 Tournament	6	12	Lake Austin	loop 360 boat ramp	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
137	147	\N	April 2023 Tournament	3	7	Lake Travis	tournament point	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
146	156	\N	January 2024 Tournament	9	19	Lake Buchanan	burnett county park	07:00:00	16:00:00	5	25.0	t	f	0.0	t	\N	angler	t
147	157	\N	February 2024 Tournament	3	7	Lake Travis	tournament point	07:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
148	158	\N	March 2024 Tournament	3	7	Lake Travis	tournament point	06:30:00	16:00:00	5	25.0	t	f	0.0	t	\N	angler	t
149	159	\N	April 2024 Tournament	5	9	Lake LBJ	yacht club & marina	06:30:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
150	160	\N	May 2024 Tournament	9	19	Lake Buchanan	burnett county park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
151	161	\N	June 2024 Tournament	3	7	Lake Travis	tournament point	00:00:00	09:00:00	5	25.0	t	f	0.0	t	\N	angler	t
152	162	\N	July 2024 Tournament	5	9	Lake LBJ	yacht club & marina	00:00:00	09:00:00	5	25.0	t	f	0.0	t	\N	angler	t
153	163	\N	August 2024 Tournament	10	21	Still House Hollow Lake	riversbend park	06:00:00	13:00:00	5	25.0	t	f	0.0	t	\N	angler	t
154	164	\N	September 2024 Tournament	1	1	Lake Belton	cedar ridge park	06:30:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
155	165	\N	October 2024 Tournament	9	19	Lake Buchanan	burnett county park	06:30:00	14:30:00	5	25.0	t	f	0.0	t	\N	angler	t
156	166	\N	November 2024 Tournament	5	9	Lake LBJ	yacht club & marina	06:30:00	14:30:00	5	25.0	t	f	0.0	t	\N	angler	t
157	167	\N	December 2024 Tournament	4	8	Inks Lake	Inks Lake State Park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
158	168	\N	January 2025 Tournament	8	18	Fayette County Reservoir	oak thicket park	07:00:00	16:00:00	5	25.0	t	f	0.0	t	\N	angler	t
159	169	\N	February 2025 Tournament	9	19	Lake Buchanan	burnett county park	07:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
160	170	\N	March 2025 Tournament	3	7	Lake Travis	tournament point	07:00:00	16:00:00	5	25.0	t	f	0.0	t	\N	angler	t
161	171	\N	April 2025 Tournament	10	21	Still House Hollow Lake	riversbend park	06:30:00	15:30:00	5	25.0	t	f	0.0	t	\N	angler	t
162	172	\N	May 2025 Tournament	3	7	Lake Travis	tournament point	06:15:00	15:30:00	5	25.0	t	f	0.0	t	\N	angler	t
163	173	\N	June 2025 Tournament	3	7	Lake Travis	tournament point	00:00:00	09:00:00	5	25.0	t	f	0.0	t	\N	angler	t
165	175	\N	September 2025 Tournament	5	9	Lake LBJ	yacht club & marina	06:30:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
164	174	\N	August 2025 Tournament	3	5	Lake Travis	mansfield dam	05:00:00	11:00:00	3	25.0	t	f	0.0	t	\N	angler	t
\.


--
-- Name: anglers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.anglers_id_seq', 424, true);


--
-- Name: calendar_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.calendar_events_id_seq', 1, false);


--
-- Name: dues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.dues_id_seq', 1, false);


--
-- Name: events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.events_id_seq', 229, true);


--
-- Name: lakes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.lakes_id_seq', 34, true);


--
-- Name: news_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.news_id_seq', 2, true);


--
-- Name: officer_positions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.officer_positions_id_seq', 7, true);


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.password_reset_tokens_id_seq', 1, false);


--
-- Name: poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.poll_options_id_seq', 528, true);


--
-- Name: poll_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.poll_votes_id_seq', 1, false);


--
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.polls_id_seq', 33, true);


--
-- Name: ramps_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.ramps_id_seq', 49, true);


--
-- Name: results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.results_id_seq', 2448, true);


--
-- Name: team_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.team_results_id_seq', 767, true);


--
-- Name: tournaments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: sabc_user
--

SELECT pg_catalog.setval('public.tournaments_id_seq', 165, true);


--
-- Name: anglers anglers_email_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.anglers
    ADD CONSTRAINT anglers_email_key UNIQUE (email);


--
-- Name: anglers anglers_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.anglers
    ADD CONSTRAINT anglers_pkey PRIMARY KEY (id);


--
-- Name: calendar_events calendar_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.calendar_events
    ADD CONSTRAINT calendar_events_pkey PRIMARY KEY (id);


--
-- Name: dues dues_angler_id_year_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.dues
    ADD CONSTRAINT dues_angler_id_year_key UNIQUE (angler_id, year);


--
-- Name: dues dues_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.dues
    ADD CONSTRAINT dues_pkey PRIMARY KEY (id);


--
-- Name: events events_date_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_date_key UNIQUE (date);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: lakes lakes_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.lakes
    ADD CONSTRAINT lakes_pkey PRIMARY KEY (id);


--
-- Name: lakes lakes_yaml_key_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.lakes
    ADD CONSTRAINT lakes_yaml_key_key UNIQUE (yaml_key);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- Name: officer_positions officer_positions_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.officer_positions
    ADD CONSTRAINT officer_positions_pkey PRIMARY KEY (id);


--
-- Name: officer_positions officer_positions_position_year_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.officer_positions
    ADD CONSTRAINT officer_positions_position_year_key UNIQUE ("position", year);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: poll_options poll_options_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_pkey PRIMARY KEY (id);


--
-- Name: poll_votes poll_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_pkey PRIMARY KEY (id);


--
-- Name: poll_votes poll_votes_poll_id_option_id_angler_id_key; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_poll_id_option_id_angler_id_key UNIQUE (poll_id, option_id, angler_id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- Name: ramps ramps_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.ramps
    ADD CONSTRAINT ramps_pkey PRIMARY KEY (id);


--
-- Name: results results_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_pkey PRIMARY KEY (id);


--
-- Name: team_results team_results_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.team_results
    ADD CONSTRAINT team_results_pkey PRIMARY KEY (id);


--
-- Name: tournaments tournaments_pkey; Type: CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.tournaments
    ADD CONSTRAINT tournaments_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sabc_user
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.anglers(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict XO4jusQcMSXQC6G1Rg0g7VjAeKDeHPC1nBXCPdck3ufZFMqiNVu0OFvvTQHARXw

