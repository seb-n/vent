CREATE TABLE users(
	user_id integer primary key,
	user_name text,
	completed bool,
	listening_complete bool
	listeners_complete bool,
	is_deleted bool,
	visited bool);

CREATE TABLE user_details(
	user_id integer primary key,
	post_count integer,
	follower_count integer,
	following_count integer,
	created_on timestamp,
	total_post_clicks integer);
