--
-- PostgreSQL database dump
--

-- Dumped from database version 15.14 (Debian 15.14-1.pgdg13+1)
-- Dumped by pg_dump version 17.5

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
-- Name: anglers; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.anglers OWNER TO postgres;

--
-- Name: events; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.events OWNER TO postgres;

--
-- Name: results; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.results OWNER TO postgres;

--
-- Name: tournaments; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.tournaments OWNER TO postgres;

--
-- Name: tournament_standings; Type: VIEW; Schema: public; Owner: postgres
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


ALTER VIEW public.tournament_standings OWNER TO postgres;

--
-- Name: angler_of_year; Type: VIEW; Schema: public; Owner: postgres
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


ALTER VIEW public.angler_of_year OWNER TO postgres;

--
-- Name: anglers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.anglers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.anglers_id_seq OWNER TO postgres;

--
-- Name: anglers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.anglers_id_seq OWNED BY public.anglers.id;


--
-- Name: calendar_events; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.calendar_events OWNER TO postgres;

--
-- Name: calendar_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.calendar_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.calendar_events_id_seq OWNER TO postgres;

--
-- Name: calendar_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.calendar_events_id_seq OWNED BY public.calendar_events.id;


--
-- Name: dues; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dues (
    id integer NOT NULL,
    angler_id integer,
    year integer NOT NULL,
    amount numeric DEFAULT 25.00,
    paid_date date,
    paid boolean DEFAULT false
);


ALTER TABLE public.dues OWNER TO postgres;

--
-- Name: dues_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dues_id_seq OWNER TO postgres;

--
-- Name: dues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dues_id_seq OWNED BY public.dues.id;


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_id_seq OWNER TO postgres;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: lakes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lakes (
    id integer NOT NULL,
    yaml_key text NOT NULL,
    display_name text NOT NULL,
    google_maps_iframe text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.lakes OWNER TO postgres;

--
-- Name: lakes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lakes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lakes_id_seq OWNER TO postgres;

--
-- Name: lakes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lakes_id_seq OWNED BY public.lakes.id;


--
-- Name: news; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.news OWNER TO postgres;

--
-- Name: news_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.news_id_seq OWNER TO postgres;

--
-- Name: news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.news_id_seq OWNED BY public.news.id;


--
-- Name: officer_positions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.officer_positions (
    id integer NOT NULL,
    angler_id integer,
    "position" text NOT NULL,
    year integer NOT NULL,
    elected_date date
);


ALTER TABLE public.officer_positions OWNER TO postgres;

--
-- Name: officer_positions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.officer_positions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.officer_positions_id_seq OWNER TO postgres;

--
-- Name: officer_positions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.officer_positions_id_seq OWNED BY public.officer_positions.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.password_reset_tokens OWNER TO postgres;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.password_reset_tokens_id_seq OWNER TO postgres;

--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: poll_options; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.poll_options (
    id integer NOT NULL,
    poll_id integer,
    option_text text NOT NULL,
    option_data text,
    display_order integer DEFAULT 0
);


ALTER TABLE public.poll_options OWNER TO postgres;

--
-- Name: poll_options_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.poll_options_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_options_id_seq OWNER TO postgres;

--
-- Name: poll_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.poll_options_id_seq OWNED BY public.poll_options.id;


--
-- Name: poll_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.poll_votes (
    id integer NOT NULL,
    poll_id integer,
    option_id integer,
    angler_id integer,
    voted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.poll_votes OWNER TO postgres;

--
-- Name: poll_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.poll_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.poll_votes_id_seq OWNER TO postgres;

--
-- Name: poll_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.poll_votes_id_seq OWNED BY public.poll_votes.id;


--
-- Name: polls; Type: TABLE; Schema: public; Owner: postgres
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


ALTER TABLE public.polls OWNER TO postgres;

--
-- Name: polls_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.polls_id_seq OWNER TO postgres;

--
-- Name: polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.polls_id_seq OWNED BY public.polls.id;


--
-- Name: ramps; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ramps (
    id integer NOT NULL,
    lake_id integer,
    name text NOT NULL,
    google_maps_iframe text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ramps OWNER TO postgres;

--
-- Name: ramps_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ramps_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ramps_id_seq OWNER TO postgres;

--
-- Name: ramps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ramps_id_seq OWNED BY public.ramps.id;


--
-- Name: results_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.results_id_seq OWNER TO postgres;

--
-- Name: results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.results_id_seq OWNED BY public.results.id;


--
-- Name: team_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.team_results (
    id integer NOT NULL,
    tournament_id integer,
    angler1_id integer,
    angler2_id integer,
    total_weight numeric DEFAULT 0.0,
    place_finish integer
);


ALTER TABLE public.team_results OWNER TO postgres;

--
-- Name: team_results_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.team_results_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.team_results_id_seq OWNER TO postgres;

--
-- Name: team_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.team_results_id_seq OWNED BY public.team_results.id;


--
-- Name: tournaments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tournaments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tournaments_id_seq OWNER TO postgres;

--
-- Name: tournaments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tournaments_id_seq OWNED BY public.tournaments.id;


--
-- Name: anglers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.anglers ALTER COLUMN id SET DEFAULT nextval('public.anglers_id_seq'::regclass);


--
-- Name: calendar_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.calendar_events ALTER COLUMN id SET DEFAULT nextval('public.calendar_events_id_seq'::regclass);


--
-- Name: dues id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dues ALTER COLUMN id SET DEFAULT nextval('public.dues_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: lakes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lakes ALTER COLUMN id SET DEFAULT nextval('public.lakes_id_seq'::regclass);


--
-- Name: news id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news ALTER COLUMN id SET DEFAULT nextval('public.news_id_seq'::regclass);


--
-- Name: officer_positions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer_positions ALTER COLUMN id SET DEFAULT nextval('public.officer_positions_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: poll_options id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_options ALTER COLUMN id SET DEFAULT nextval('public.poll_options_id_seq'::regclass);


--
-- Name: poll_votes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes ALTER COLUMN id SET DEFAULT nextval('public.poll_votes_id_seq'::regclass);


--
-- Name: polls id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls ALTER COLUMN id SET DEFAULT nextval('public.polls_id_seq'::regclass);


--
-- Name: ramps id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ramps ALTER COLUMN id SET DEFAULT nextval('public.ramps_id_seq'::regclass);


--
-- Name: results id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results ALTER COLUMN id SET DEFAULT nextval('public.results_id_seq'::regclass);


--
-- Name: team_results id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_results ALTER COLUMN id SET DEFAULT nextval('public.team_results_id_seq'::regclass);


--
-- Name: tournaments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournaments ALTER COLUMN id SET DEFAULT nextval('public.tournaments_id_seq'::regclass);


--
-- Data for Name: anglers; Type: TABLE DATA; Schema: public; Owner: postgres
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
375	Darryl Ackerman	Temp@gmail.com	t	f	\N	\N	+15122895477	2025-09-29 13:35:59.225986
376	Doc TBD	TBD@gmail.com	f	f	\N	\N	\N	2025-09-29 13:35:59.226782
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
389	Joana TBD	Temp_2@gmail.com	f	f	\N	\N	+15124567890	2025-09-29 13:35:59.237002
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
\.


--
-- Data for Name: calendar_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.calendar_events (id, title, event_date, event_type, description, created_by, created_at) FROM stdin;
\.


--
-- Data for Name: dues; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dues (id, angler_id, year, amount, paid_date, paid) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.events (id, date, year, name, description, event_type, start_time, weigh_in_time, lake_name, ramp_name, entry_fee, is_cancelled, holiday_name) FROM stdin;
137	2023-01-22	2023	January 2023 Tournament	Event #1	sabc_tournament	06:00:00	15:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
145	2023-02-26	2023	February 2025 Tournament	Event #2	sabc_tournament	06:00:00	15:00:00	Lake Belton	cedar ridge park	25.0	f	\N
146	2023-03-26	2023	March 2023 Tournament	Event #3	sabc_tournament	06:00:00	15:00:00	Lake Buchanan	Burnett County Park	25.0	f	\N
147	2023-04-23	2023	April 2023 Tournament	Event #4	sabc_tournament	06:00:00	15:00:00	Lake Travis	tournament point	25.0	f	\N
148	2023-05-21	2023	May 2023 Tournament	Event #5	sabc_tournament	06:00:00	15:00:00	Still House Hollow Lake	riversbend park	25.0	f	\N
149	2023-06-25	2023	June 2023 Tournament	Event #6	sabc_tournament	05:00:00	13:00:00	Lake Buchanan	Burnett County Park	25.0	f	\N
151	2023-08-27	2023	August 2023 Tournament	Event #8	sabc_tournament	00:00:00	09:00:00	Lake LBJ	yacht club & marina	25.0	f	\N
150	2023-07-23	2023	July 2023 Tournament	Event #7	sabc_tournament	00:00:00	09:00:00	Lake Austin	loop 360 boat ramp	25.0	f	\N
152	2023-09-24	2023	September 2023 Tournament	Event #9	sabc_tournament	07:00:00	15:00:00	Still House Hollow Lake	riversbend park	25.0	f	\N
153	2023-10-22	2023	October 2025 Tournament	Event #10	sabc_tournament	07:00:00	15:00:00	Canyon Lake	canyon lake boat ramp 17	25.0	f	\N
154	2023-11-19	2023	November 2023 Tournament	Event #11	sabc_tournament	06:00:00	15:00:00	Lake Travis	tournament point	25.0	f	\N
155	2023-12-03	2023	December 2023 Tournament	Event #12	sabc_tournament	06:00:00	15:00:00	Lake Austin	loop 360 boat ramp	25.0	f	\N
\.


--
-- Data for Name: lakes; Type: TABLE DATA; Schema: public; Owner: postgres
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
-- Data for Name: news; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.news (id, title, content, author_id, created_at, updated_at, published, priority, expires_at, last_edited_by) FROM stdin;
1	New Site!	Our new website is up and active. Key changes are: We can vote on everything (and anything) 100% on-line! We've added Latest News section, for updates to the site! Look at the Polls section for voting on tournament details and club motions. Yay!	278	2025-09-29 22:00:25.915866	2025-09-30 21:26:36.696757	t	0	\N	278
\.


--
-- Data for Name: officer_positions; Type: TABLE DATA; Schema: public; Owner: postgres
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
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.password_reset_tokens (id, user_id, token, expires_at, used, created_at, used_at) FROM stdin;
\.


--
-- Data for Name: poll_options; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.poll_options (id, poll_id, option_text, option_data, display_order) FROM stdin;
\.


--
-- Data for Name: poll_votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.poll_votes (id, poll_id, option_id, angler_id, voted_at) FROM stdin;
\.


--
-- Data for Name: polls; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.polls (id, title, description, poll_type, event_id, created_by, created_at, starts_at, closes_at, closed, multiple_votes, winning_option_id) FROM stdin;
\.


--
-- Data for Name: ramps; Type: TABLE DATA; Schema: public; Owner: postgres
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
-- Data for Name: results; Type: TABLE DATA; Schema: public; Owner: postgres
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
\.


--
-- Data for Name: team_results; Type: TABLE DATA; Schema: public; Owner: postgres
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
474	135	407	400	14.78	1
475	135	364	370	14.76	2
476	135	366	380	11.10	3
477	135	382	383	6.05	4
478	135	378	371	1.38	5
479	135	417	387	0	6
480	135	373	\N	0	7
481	135	395	\N	0	8
482	135	411	\N	0	9
483	135	385	\N	0	10
\.


--
-- Data for Name: tournaments; Type: TABLE DATA; Schema: public; Owner: postgres
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
137	147	\N	April 2023 Tournament	3	7	\N	tournament point	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
138	148	\N	May 2023 Tournament	10	21	Still House Hollow Lake	riversbend park	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
139	149	\N	June 2023 Tournament	9	19	Lake Buchanan	Burnett County Park	05:00:00	13:00:00	5	25.0	t	f	0.0	t	\N	angler	t
145	155	\N	December 2023 Tournament	6	12	Lake Austin	loop 360 boat ramp	06:00:00	15:00:00	5	25.0	t	f	0.0	t	\N	angler	t
\.


--
-- Name: anglers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.anglers_id_seq', 424, true);


--
-- Name: calendar_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.calendar_events_id_seq', 1, false);


--
-- Name: dues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dues_id_seq', 1, false);


--
-- Name: events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.events_id_seq', 155, true);


--
-- Name: lakes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.lakes_id_seq', 34, true);


--
-- Name: news_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.news_id_seq', 2, true);


--
-- Name: officer_positions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.officer_positions_id_seq', 7, true);


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.password_reset_tokens_id_seq', 1, false);


--
-- Name: poll_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.poll_options_id_seq', 208, true);


--
-- Name: poll_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.poll_votes_id_seq', 1, false);


--
-- Name: polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.polls_id_seq', 13, true);


--
-- Name: ramps_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ramps_id_seq', 49, true);


--
-- Name: results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.results_id_seq', 1967, true);


--
-- Name: team_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.team_results_id_seq', 483, true);


--
-- Name: tournaments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tournaments_id_seq', 145, true);


--
-- Name: anglers anglers_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.anglers
    ADD CONSTRAINT anglers_email_key UNIQUE (email);


--
-- Name: anglers anglers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.anglers
    ADD CONSTRAINT anglers_pkey PRIMARY KEY (id);


--
-- Name: calendar_events calendar_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.calendar_events
    ADD CONSTRAINT calendar_events_pkey PRIMARY KEY (id);


--
-- Name: dues dues_angler_id_year_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dues
    ADD CONSTRAINT dues_angler_id_year_key UNIQUE (angler_id, year);


--
-- Name: dues dues_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dues
    ADD CONSTRAINT dues_pkey PRIMARY KEY (id);


--
-- Name: events events_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_date_key UNIQUE (date);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: lakes lakes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lakes
    ADD CONSTRAINT lakes_pkey PRIMARY KEY (id);


--
-- Name: lakes lakes_yaml_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lakes
    ADD CONSTRAINT lakes_yaml_key_key UNIQUE (yaml_key);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- Name: officer_positions officer_positions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer_positions
    ADD CONSTRAINT officer_positions_pkey PRIMARY KEY (id);


--
-- Name: officer_positions officer_positions_position_year_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.officer_positions
    ADD CONSTRAINT officer_positions_position_year_key UNIQUE ("position", year);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: poll_options poll_options_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_options
    ADD CONSTRAINT poll_options_pkey PRIMARY KEY (id);


--
-- Name: poll_votes poll_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_pkey PRIMARY KEY (id);


--
-- Name: poll_votes poll_votes_poll_id_option_id_angler_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_poll_id_option_id_angler_id_key UNIQUE (poll_id, option_id, angler_id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (id);


--
-- Name: ramps ramps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ramps
    ADD CONSTRAINT ramps_pkey PRIMARY KEY (id);


--
-- Name: results results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results
    ADD CONSTRAINT results_pkey PRIMARY KEY (id);


--
-- Name: team_results team_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_results
    ADD CONSTRAINT team_results_pkey PRIMARY KEY (id);


--
-- Name: tournaments tournaments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournaments
    ADD CONSTRAINT tournaments_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.anglers(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

