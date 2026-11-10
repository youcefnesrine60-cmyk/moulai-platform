-- Generated from executed main Alembic history; apply with ON_ERROR_STOP and a single transaction.
-- Never stamp, auto-retry or apply to the historical project.
DO $attest$ BEGIN
IF current_database() IS DISTINCT FROM 'moulai_staging_rehearsal'
OR current_user IS DISTINCT FROM 'moulai_staging_migrator'
OR current_setting('neon.project_id',true) IS DISTINCT FROM 'sparkling-rice-23028300'
OR current_setting('neon.branch_id',true) IS DISTINCT FROM 'br-lucky-smoke-b9edyxoe'
OR current_setting('neon.endpoint_id',true) IS DISTINCT FROM 'ep-odd-wildflower-b9wacgg0'
THEN RAISE EXCEPTION 'staging_migration_target_refused'; END IF;
END $attest$;
SET LOCAL statement_timeout='120s';
SET LOCAL lock_timeout='5s';
DO $state$ BEGIN IF EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public') THEN RAISE EXCEPTION 'staging_empty_database_required'; END IF; END $state$;
COMMENT ON DATABASE moulai_staging_rehearsal IS 'moulai-staging:bf4de394885f4d208b018f5056366f59';
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE TABLE admins (
	chat_id BIGINT NOT NULL,
	username VARCHAR(255),
	full_name VARCHAR(255),
	role VARCHAR(50) NOT NULL,
	password_hash VARCHAR(255),
	is_active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE branch_pricing (
	min_branches INTEGER NOT NULL,
	max_branches INTEGER,
	price_per_branch FLOAT NOT NULL,
	active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE branches (
	restaurant_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	phone VARCHAR(20),
	wilaya VARCHAR(100),
	lat FLOAT,
	lng FLOAT,
	is_active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE categories (
	restaurant_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	sort_order INTEGER,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE feature_pricing (
	feature_id INTEGER NOT NULL,
	billing_cycle VARCHAR(50) NOT NULL,
	price FLOAT NOT NULL,
	active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE feature_usage_counters (
	restaurant_id INTEGER NOT NULL,
	feature_id INTEGER NOT NULL,
	usage_count INTEGER NOT NULL,
	period_year INTEGER,
	period_month INTEGER,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE feature_usage_limits (
	plan_id INTEGER NOT NULL,
	feature_id INTEGER NOT NULL,
	monthly_limit INTEGER,
	limit_type VARCHAR(50),
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE features (
	code VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (code)
);

CREATE TABLE loyalty_discounts (
	years_required INTEGER NOT NULL,
	discount_percent FLOAT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE multi_restaurant_discounts (
	min_restaurants INTEGER NOT NULL,
	discount_percent FLOAT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE option_groups (
	product_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	required BOOLEAN,
	multiple_choice BOOLEAN,
	sort_order INTEGER,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE order_item_options (
	order_item_id BIGINT NOT NULL,
	option_group_name VARCHAR(255) NOT NULL,
	option_name VARCHAR(255) NOT NULL,
	additional_price FLOAT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE order_items (
	order_id BIGINT NOT NULL,
	product_id INTEGER NOT NULL,
	product_name VARCHAR(255) NOT NULL,
	unit_price FLOAT NOT NULL,
	quantity INTEGER NOT NULL,
	total_price FLOAT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE order_payments (
	order_id BIGINT NOT NULL,
	payment_method VARCHAR(50) NOT NULL,
	payment_status VARCHAR(50) NOT NULL,
	amount FLOAT NOT NULL,
	transaction_reference VARCHAR(255),
	paid_at TIMESTAMP WITHOUT TIME ZONE,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE order_status_history (
	order_id BIGINT NOT NULL,
	old_status VARCHAR(50),
	new_status VARCHAR(50) NOT NULL,
	changed_by_employee_id INTEGER,
	note TEXT,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE orders (
	restaurant_id INTEGER NOT NULL,
	branch_id INTEGER,
	table_id INTEGER,
	employee_id INTEGER,
	order_number VARCHAR(50) NOT NULL,
	order_type VARCHAR(30) NOT NULL,
	delivery_address TEXT,
	customer_note TEXT,
	status VARCHAR(50) NOT NULL,
	subtotal_amount FLOAT NOT NULL,
	discount_amount FLOAT NOT NULL,
	tax_amount FLOAT NOT NULL,
	delivery_amount FLOAT NOT NULL,
	total_amount FLOAT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE owners (
	chat_id BIGINT NOT NULL,
	full_name VARCHAR(255),
	phone VARCHAR(20),
	email VARCHAR(255),
	registration_status VARCHAR(50) NOT NULL,
	trial_used BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE payments (
	owner_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	subscription_id INTEGER,
	payment_method VARCHAR(50) NOT NULL,
	amount FLOAT NOT NULL,
	status VARCHAR(50) NOT NULL,
	external_reference TEXT,
	paid_at TIMESTAMP WITHOUT TIME ZONE,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE plan_features (
	plan_id INTEGER NOT NULL,
	feature_id INTEGER NOT NULL,
	included BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE product_options (
	group_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	extra_price FLOAT,
	is_available BOOLEAN,
	sort_order INTEGER,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE products (
	restaurant_id INTEGER NOT NULL,
	category_id INTEGER NOT NULL,
	name TEXT NOT NULL,
	description TEXT,
	price FLOAT NOT NULL,
	image_url TEXT,
	is_available BOOLEAN,
	sort_order INTEGER,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE promotions (
	name VARCHAR(255) NOT NULL,
	discount_percent FLOAT NOT NULL,
	starts_at TIMESTAMP WITHOUT TIME ZONE,
	expires_at TIMESTAMP WITHOUT TIME ZONE,
	active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE registration_requests (
	chat_id BIGINT NOT NULL,
	full_name TEXT NOT NULL,
	owner_phone TEXT NOT NULL,
	email TEXT,
	restaurant_name TEXT NOT NULL,
	restaurant_type TEXT NOT NULL,
	restaurant_phone TEXT NOT NULL,
	wilaya TEXT,
	lat FLOAT,
	lng FLOAT,
	status TEXT NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE restaurant_branches (
	group_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE restaurant_groups (
	owner_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE restaurant_metrics (
	restaurant_id INTEGER NOT NULL,
	products_count INTEGER NOT NULL,
	categories_count INTEGER NOT NULL,
	monthly_orders INTEGER NOT NULL,
	average_order_value FLOAT NOT NULL,
	PRIMARY KEY (restaurant_id)
);

CREATE TABLE restaurant_order_counters (
	restaurant_id INTEGER NOT NULL,
	last_number BIGINT NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (restaurant_id)
);

CREATE TABLE restaurants (
	owner_id INTEGER NOT NULL,
	name VARCHAR(255) NOT NULL,
	type VARCHAR(100) NOT NULL,
	phone VARCHAR(20) NOT NULL,
	wilaya VARCHAR(100) NOT NULL,
	lat FLOAT,
	lng FLOAT,
	is_active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	CONSTRAINT uq_restaurant_location UNIQUE (owner_id, name, phone, wilaya, lat, lng)
);

CREATE TABLE subscription_feature_requests (
	subscription_id INTEGER NOT NULL,
	feature_id INTEGER NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE subscription_features (
	subscription_id INTEGER NOT NULL,
	feature_id INTEGER NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE subscription_plans (
	code VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	description TEXT,
	base_price FLOAT NOT NULL,
	plan_discount_percent FLOAT NOT NULL,
	display_order INTEGER,
	active BOOLEAN,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	UNIQUE (code)
);

CREATE TABLE subscriptions (
	owner_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	plan_id INTEGER NOT NULL,
	billing_cycle VARCHAR(50) NOT NULL,
	amount FLOAT NOT NULL,
	starts_at TIMESTAMP WITHOUT TIME ZONE,
	expires_at TIMESTAMP WITHOUT TIME ZONE,
	status VARCHAR(50) NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE TABLE users (
	chat_id BIGINT,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_admins_chat_id ON admins (chat_id);

CREATE INDEX ix_admins_id ON admins (id);

CREATE INDEX ix_admins_username ON admins (username);

CREATE INDEX ix_branch_pricing_id ON branch_pricing (id);

ALTER TABLE branches ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX idx_branches_restaurant ON branches (restaurant_id);

CREATE INDEX ix_branches_id ON branches (id);

ALTER TABLE categories ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX ix_categories_id ON categories (id);

ALTER TABLE feature_pricing ADD FOREIGN KEY(feature_id) REFERENCES features (id) ON DELETE CASCADE;

CREATE INDEX ix_feature_pricing_id ON feature_pricing (id);

ALTER TABLE feature_usage_counters ADD FOREIGN KEY(feature_id) REFERENCES features (id) ON DELETE CASCADE;

ALTER TABLE feature_usage_counters ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX ix_feature_usage_counters_id ON feature_usage_counters (id);

ALTER TABLE feature_usage_limits ADD FOREIGN KEY(feature_id) REFERENCES features (id);

ALTER TABLE feature_usage_limits ADD FOREIGN KEY(plan_id) REFERENCES subscription_plans (id);

CREATE INDEX ix_feature_usage_limits_id ON feature_usage_limits (id);

CREATE INDEX ix_features_id ON features (id);

CREATE INDEX ix_loyalty_discounts_id ON loyalty_discounts (id);

CREATE INDEX ix_multi_restaurant_discounts_id ON multi_restaurant_discounts (id);

ALTER TABLE option_groups ADD FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE;

CREATE INDEX ix_option_groups_id ON option_groups (id);

ALTER TABLE order_item_options ADD FOREIGN KEY(order_item_id) REFERENCES order_items (id) ON DELETE CASCADE;

CREATE INDEX ix_order_item_options_id ON order_item_options (id);

ALTER TABLE order_items ADD FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE;

ALTER TABLE order_items ADD FOREIGN KEY(product_id) REFERENCES products (id);

CREATE INDEX ix_order_items_id ON order_items (id);

ALTER TABLE order_payments ADD FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE;

CREATE INDEX ix_order_payments_id ON order_payments (id);

ALTER TABLE order_status_history ADD FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE;

CREATE INDEX ix_order_status_history_id ON order_status_history (id);

ALTER TABLE orders ADD FOREIGN KEY(branch_id) REFERENCES branches (id) ON DELETE SET NULL;

ALTER TABLE orders ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX idx_orders_branch ON orders (branch_id);

CREATE INDEX idx_orders_created_at ON orders (created_at);

CREATE INDEX idx_orders_restaurant ON orders (restaurant_id);

CREATE UNIQUE INDEX idx_orders_restaurant_order_number ON orders (restaurant_id, order_number);

CREATE INDEX idx_orders_status ON orders (status);

CREATE INDEX ix_orders_id ON orders (id);

CREATE UNIQUE INDEX ix_owners_chat_id ON owners (chat_id);

CREATE INDEX ix_owners_id ON owners (id);

ALTER TABLE payments ADD FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE CASCADE;

ALTER TABLE payments ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

ALTER TABLE payments ADD FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE SET NULL;

CREATE INDEX ix_payments_id ON payments (id);

ALTER TABLE plan_features ADD FOREIGN KEY(feature_id) REFERENCES features (id) ON DELETE CASCADE;

ALTER TABLE plan_features ADD FOREIGN KEY(plan_id) REFERENCES subscription_plans (id) ON DELETE CASCADE;

CREATE INDEX ix_plan_features_id ON plan_features (id);

ALTER TABLE product_options ADD FOREIGN KEY(group_id) REFERENCES option_groups (id) ON DELETE CASCADE;

CREATE INDEX ix_product_options_id ON product_options (id);

ALTER TABLE products ADD FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE;

ALTER TABLE products ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX ix_products_id ON products (id);

CREATE INDEX ix_promotions_id ON promotions (id);

CREATE INDEX ix_registration_requests_id ON registration_requests (id);

ALTER TABLE restaurant_branches ADD FOREIGN KEY(group_id) REFERENCES restaurant_groups (id) ON DELETE CASCADE;

ALTER TABLE restaurant_branches ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

CREATE INDEX ix_restaurant_branches_id ON restaurant_branches (id);

ALTER TABLE restaurant_groups ADD FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE CASCADE;

CREATE INDEX ix_restaurant_groups_id ON restaurant_groups (id);

ALTER TABLE restaurant_metrics ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

ALTER TABLE restaurant_order_counters ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

ALTER TABLE restaurants ADD FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE CASCADE;

CREATE INDEX ix_restaurants_id ON restaurants (id);

ALTER TABLE subscription_feature_requests ADD FOREIGN KEY(feature_id) REFERENCES features (id) ON DELETE CASCADE;

ALTER TABLE subscription_feature_requests ADD FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE;

CREATE INDEX idx_subscription_feature_requests_feature ON subscription_feature_requests (feature_id);

CREATE INDEX idx_subscription_feature_requests_subscription ON subscription_feature_requests (subscription_id);

CREATE INDEX ix_subscription_feature_requests_id ON subscription_feature_requests (id);

ALTER TABLE subscription_features ADD FOREIGN KEY(feature_id) REFERENCES features (id) ON DELETE CASCADE;

ALTER TABLE subscription_features ADD FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE;

CREATE INDEX ix_subscription_features_id ON subscription_features (id);

CREATE INDEX ix_subscription_plans_id ON subscription_plans (id);

ALTER TABLE subscriptions ADD FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE CASCADE;

ALTER TABLE subscriptions ADD FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

ALTER TABLE subscriptions ADD FOREIGN KEY(plan_id) REFERENCES subscription_plans (id);

CREATE INDEX ix_subscriptions_id ON subscriptions (id);

CREATE UNIQUE INDEX uq_active_subscription ON subscriptions (restaurant_id) WHERE status IN ('trial', 'active');

CREATE UNIQUE INDEX ix_users_chat_id ON users (chat_id);

CREATE INDEX ix_users_id ON users (id);


CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);


CREATE TABLE agents (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	name VARCHAR(100) DEFAULT 'My Assistant' NOT NULL,
	description TEXT,
	language VARCHAR(10) DEFAULT 'ar',
	tone VARCHAR(50) DEFAULT 'professional',
	is_active BOOLEAN DEFAULT true NOT NULL,
	config JSON,
	ai_config JSON,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE
);

CREATE INDEX ix_agents_id ON agents (id);


CREATE TABLE channels (
	id SERIAL NOT NULL,
	agent_id INTEGER NOT NULL,
	type VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	config JSON,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE
);

CREATE INDEX ix_channels_id ON channels (id);


CREATE TABLE conversations (
	id SERIAL NOT NULL,
	agent_id INTEGER NOT NULL,
	channel_id INTEGER NOT NULL,
	user_id VARCHAR(255) NOT NULL,
	user_name VARCHAR(255),
	is_active BOOLEAN DEFAULT true NOT NULL,
	context JSON,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(agent_id) REFERENCES agents (id) ON DELETE CASCADE,
	FOREIGN KEY(channel_id) REFERENCES channels (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversations_id ON conversations (id);


CREATE TABLE messages (
	id SERIAL NOT NULL,
	conversation_id INTEGER NOT NULL,
	role VARCHAR(20) NOT NULL,
	content TEXT NOT NULL,
	intent VARCHAR(100),
	confidence FLOAT,
	entities JSON,
	meta_data JSON,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX ix_messages_id ON messages (id);

ALTER TABLE users ADD COLUMN consent BOOLEAN DEFAULT false;

ALTER TABLE users ADD CONSTRAINT users_chat_id_key UNIQUE (chat_id);

ALTER TABLE restaurants ADD COLUMN group_id INTEGER;

ALTER TABLE restaurants ADD CONSTRAINT fk_restaurant_group FOREIGN KEY(group_id) REFERENCES restaurant_groups (id) ON DELETE SET NULL;

INSERT INTO alembic_version (version_num) VALUES ('17b6b58772b7') RETURNING alembic_version.version_num;

ALTER TABLE users ADD COLUMN customer_name VARCHAR(255);

ALTER TABLE users ADD COLUMN customer_phone VARCHAR(20);

ALTER TABLE orders ADD COLUMN user_id INTEGER;

ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='2d999b8ed18f' WHERE alembic_version.version_num = '17b6b58772b7';

ALTER TABLE payments ADD COLUMN user_id INTEGER;

ALTER TABLE payments ADD CONSTRAINT fk_payments_user FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL;

CREATE INDEX idx_payments_user_id ON payments (user_id);

UPDATE alembic_version SET version_num='4c3017ab0067' WHERE alembic_version.version_num = '2d999b8ed18f';


CREATE TABLE admin_logs (
	id SERIAL NOT NULL,
	admin_id INTEGER NOT NULL,
	action VARCHAR(50) NOT NULL,
	resource VARCHAR(50),
	resource_id INTEGER,
	details TEXT,
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(admin_id) REFERENCES admins (id) ON DELETE CASCADE
);

CREATE INDEX ix_admin_logs_id ON admin_logs (id);


CREATE TABLE admin_sessions (
	id SERIAL NOT NULL,
	admin_id INTEGER NOT NULL,
	session_token VARCHAR(255) NOT NULL,
	ip_address VARCHAR(45),
	user_agent VARCHAR(255),
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	last_activity TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(admin_id) REFERENCES admins (id) ON DELETE CASCADE,
	UNIQUE (session_token)
);

CREATE INDEX ix_admin_sessions_id ON admin_sessions (id);

CREATE INDEX idx_admin_logs_admin_id ON admin_logs (admin_id);

CREATE INDEX idx_admin_logs_action ON admin_logs (action);

CREATE INDEX idx_admin_sessions_admin_id ON admin_sessions (admin_id);

CREATE INDEX idx_admin_sessions_session_token ON admin_sessions (session_token);

UPDATE alembic_version SET version_num='83fe3deff863' WHERE alembic_version.version_num = '4c3017ab0067';

ALTER TABLE restaurants ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();

COMMENT ON COLUMN restaurants.updated_at IS 'تاريخ ووقت آخر تحديث';

UPDATE alembic_version SET version_num='1452679b0eb0' WHERE alembic_version.version_num = '83fe3deff863';

ALTER TABLE owners ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();

COMMENT ON COLUMN owners.updated_at IS 'تاريخ ووقت آخر تحديث';

UPDATE alembic_version SET version_num='fd29befe8baf' WHERE alembic_version.version_num = '1452679b0eb0';

ALTER TABLE subscriptions ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();

COMMENT ON COLUMN subscriptions.updated_at IS 'تاريخ ووقت آخر تحديث';

UPDATE alembic_version SET version_num='dc626cfd1aaf' WHERE alembic_version.version_num = 'fd29befe8baf';

ALTER TABLE restaurant_metrics ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();

COMMENT ON COLUMN restaurant_metrics.updated_at IS 'تاريخ ووقت آخر تحديث';

UPDATE alembic_version SET version_num='888e43fc4f9b' WHERE alembic_version.version_num = 'dc626cfd1aaf';

ALTER TABLE restaurant_metrics ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now();

COMMENT ON COLUMN restaurant_metrics.created_at IS 'تاريخ الإنشاء';

UPDATE alembic_version SET version_num='a9a5aec4604b' WHERE alembic_version.version_num = '888e43fc4f9b';

ALTER TABLE registration_requests ADD COLUMN owner_id INTEGER;

COMMENT ON COLUMN registration_requests.owner_id IS 'معرف المالك المرتبط (بعد الموافقة)';

ALTER TABLE registration_requests ADD CONSTRAINT fk_registration_requests_owner FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='43d4b74c965c' WHERE alembic_version.version_num = 'a9a5aec4604b';


CREATE TABLE restaurant_payment_settings (
	id SERIAL NOT NULL,
	restaurant_id INTEGER NOT NULL,
	allow_cash BOOLEAN DEFAULT true NOT NULL,
	allow_card BOOLEAN DEFAULT true NOT NULL,
	allow_ccp BOOLEAN DEFAULT false NOT NULL,
	allow_baridimob BOOLEAN DEFAULT false NOT NULL,
	allow_stripe BOOLEAN DEFAULT false NOT NULL,
	allow_paypal BOOLEAN DEFAULT false NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	PRIMARY KEY (id),
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
	CONSTRAINT uq_restaurant_payment_settings UNIQUE (restaurant_id),
	UNIQUE (restaurant_id)
);

CREATE INDEX ix_restaurant_payment_settings_id ON restaurant_payment_settings (id);

CREATE INDEX idx_restaurant_payment_settings_restaurant ON restaurant_payment_settings (restaurant_id);

UPDATE alembic_version SET version_num='084c58bd26bf' WHERE alembic_version.version_num = '43d4b74c965c';

ALTER TABLE branch_pricing ADD COLUMN plan_id INTEGER;

COMMENT ON COLUMN branch_pricing.plan_id IS 'معرف خطة الاشتراك (اختياري)';

ALTER TABLE branch_pricing ADD CONSTRAINT fk_branch_pricing_plan FOREIGN KEY(plan_id) REFERENCES subscription_plans (id) ON DELETE CASCADE;

ALTER TABLE loyalty_discounts ADD COLUMN owner_id INTEGER;

COMMENT ON COLUMN loyalty_discounts.owner_id IS 'معرف المالك (اختياري)';

ALTER TABLE loyalty_discounts ADD CONSTRAINT fk_loyalty_discounts_owner FOREIGN KEY(owner_id) REFERENCES owners (id) ON DELETE CASCADE;

ALTER TABLE promotions ADD COLUMN restaurant_id INTEGER;

COMMENT ON COLUMN promotions.restaurant_id IS 'معرف المطعم (اختياري)';

ALTER TABLE promotions ADD CONSTRAINT fk_promotions_restaurant FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='9a92b84b5b11' WHERE alembic_version.version_num = '084c58bd26bf';


CREATE TABLE complaints (
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	user_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	order_id INTEGER,
	description TEXT NOT NULL,
	status VARCHAR(30) DEFAULT 'open' NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL,
	FOREIGN KEY(restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX idx_complaints_restaurant_status ON complaints (restaurant_id, status);

CREATE INDEX idx_complaints_user ON complaints (user_id);

CREATE INDEX idx_complaints_order ON complaints (order_id);

UPDATE alembic_version SET version_num='c3a5f018d7e2' WHERE alembic_version.version_num = '9a92b84b5b11';

ALTER TABLE owners ADD COLUMN auth_subject VARCHAR(255);

CREATE UNIQUE INDEX ix_owners_auth_subject ON owners (auth_subject);

UPDATE alembic_version SET version_num='6bf21d4a8c30' WHERE alembic_version.version_num = 'c3a5f018d7e2';


CREATE TABLE roles (
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	code VARCHAR(64) NOT NULL,
	name VARCHAR(128) NOT NULL,
	description TEXT,
	is_active BOOLEAN DEFAULT true NOT NULL,
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_roles_code ON roles (code);


CREATE TABLE permissions (
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	code VARCHAR(128) NOT NULL,
	name VARCHAR(128) NOT NULL,
	description TEXT,
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_permissions_code ON permissions (code);


CREATE TABLE role_permissions (
	role_id INTEGER NOT NULL,
	permission_id INTEGER NOT NULL,
	PRIMARY KEY (role_id, permission_id),
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE,
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

ALTER TABLE admins ADD COLUMN role_id INTEGER;

ALTER TABLE admins ADD CONSTRAINT fk_admins_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE SET NULL;

CREATE INDEX ix_admins_role_id ON admins (role_id);

INSERT INTO roles (code, name, description, is_active) VALUES ('super_admin', 'Super administrator', 'Full platform authority', true), ('admin', 'Administrator', 'Restaurant and operations management', true), ('support', 'Support', 'Read and complaint support', true) ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, is_active = EXCLUDED.is_active;

INSERT INTO permissions (code, name, description) SELECT code, code, code FROM unnest(ARRAY['*','restaurants.read','restaurants.manage','branches.manage','catalog.manage','orders.read','orders.manage','subscriptions.read','subscriptions.manage','reports.read','complaints.manage','admins.manage','rbac.manage']::text[]) AS code ON CONFLICT (code) DO NOTHING;

UPDATE admins SET role_id = roles.id FROM roles WHERE admins.role = roles.code AND admins.role_id IS NULL;

INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.code = 'super_admin' ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN ('restaurants.read','restaurants.manage','branches.manage','catalog.manage','orders.read','orders.manage','subscriptions.read','subscriptions.manage','reports.read','complaints.manage') WHERE r.code = 'admin' ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id) SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code IN ('restaurants.read','orders.read','subscriptions.read','reports.read','complaints.manage') WHERE r.code = 'support' ON CONFLICT DO NOTHING;

UPDATE alembic_version SET version_num='a91e7c2b4d10' WHERE alembic_version.version_num = '6bf21d4a8c30';

ALTER TABLE payments ADD COLUMN payment_provider VARCHAR(50);

ALTER TABLE payments ADD COLUMN currency VARCHAR(3) DEFAULT 'DZD' NOT NULL;

UPDATE payments SET payment_provider = 'manual_transfer' WHERE payment_method IN ('ccp', 'baridimob');

ALTER TABLE admins ADD COLUMN auth_subject VARCHAR(255);

ALTER TABLE admins ADD CONSTRAINT uq_admins_auth_subject UNIQUE (auth_subject);


CREATE TABLE manual_payment_receipts (
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	payment_id INTEGER NOT NULL,
	transaction_reference VARCHAR(120) NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	media_type VARCHAR(50) NOT NULL,
	content BYTEA NOT NULL,
	review_status VARCHAR(20) NOT NULL,
	reviewed_by INTEGER,
	reviewed_at TIMESTAMP WITHOUT TIME ZONE,
	received_amount NUMERIC(12, 2),
	received_currency VARCHAR(3),
	review_note TEXT,
	PRIMARY KEY (id),
	CHECK (review_status IN ('pending', 'approved', 'rejected')),
	CHECK (octet_length(content) BETWEEN 1 AND 2097152),
	UNIQUE (payment_id),
	FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE RESTRICT,
	UNIQUE (transaction_reference),
	UNIQUE (sha256),
	FOREIGN KEY(reviewed_by) REFERENCES admins (id) ON DELETE SET NULL
);


CREATE TABLE manual_payment_audit (
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
	payment_id INTEGER NOT NULL,
	receipt_id INTEGER NOT NULL,
	owner_id INTEGER NOT NULL,
	admin_id INTEGER,
	action VARCHAR(30) NOT NULL,
	details JSON NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE RESTRICT,
	FOREIGN KEY(receipt_id) REFERENCES manual_payment_receipts (id) ON DELETE RESTRICT,
	FOREIGN KEY(admin_id) REFERENCES admins (id) ON DELETE SET NULL
);

CREATE INDEX ix_manual_payment_audit_payment_id ON manual_payment_audit (payment_id);

INSERT INTO permissions (code, name, description) VALUES ('payments.review', 'Review manual payments', 'Independently verify received subscription funds') ON CONFLICT (code) DO NOTHING;

UPDATE alembic_version SET version_num='c413b7918a20' WHERE alembic_version.version_num = 'a91e7c2b4d10';


CREATE TABLE identities (
	issuer VARCHAR(1024) COLLATE "C" NOT NULL,
	subject VARCHAR(255) COLLATE "C" NOT NULL,
	status VARCHAR(16) DEFAULT 'suspended' NOT NULL,
	revision BIGINT DEFAULT '1' NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_identities PRIMARY KEY (id),
	CONSTRAINT ck_identity_ascii CHECK (octet_length(issuer) = length(issuer) AND octet_length(subject) = length(subject) AND issuer !~ '[[:cntrl:]]' AND subject !~ '[[:cntrl:]]'),
	CONSTRAINT ck_identity_issuer CHECK (length(issuer) BETWEEN 1 AND 1024 AND issuer = trim(issuer) AND issuer LIKE 'https://%'),
	CONSTRAINT ck_identity_revision CHECK (revision > 0),
	CONSTRAINT ck_identity_status CHECK (status IN ('active','suspended','retired')),
	CONSTRAINT ck_identity_subject CHECK (length(subject) BETWEEN 1 AND 255 AND subject = trim(subject)),
	CONSTRAINT uq_identities_issuer_subject UNIQUE (issuer, subject)
);


CREATE TABLE organizations (
	name VARCHAR(255) NOT NULL,
	status VARCHAR(16) DEFAULT 'draft' NOT NULL,
	revision BIGINT DEFAULT '1' NOT NULL,
	tenant_enforced_at TIMESTAMP WITH TIME ZONE,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_organizations PRIMARY KEY (id),
	CONSTRAINT ck_org_enforcement CHECK (status != 'active' OR tenant_enforced_at IS NOT NULL),
	CONSTRAINT ck_org_name CHECK (length(trim(name)) BETWEEN 1 AND 255 AND name = trim(name)),
	CONSTRAINT ck_org_revision CHECK (revision > 0),
	CONSTRAINT ck_org_status CHECK (status IN ('draft','active','suspended','archived'))
);


CREATE TABLE tenant_roles (
	code VARCHAR(16) NOT NULL,
	policy_revision BIGINT DEFAULT '1' NOT NULL,
	CONSTRAINT pk_tenant_roles PRIMARY KEY (code),
	CONSTRAINT ck_tenant_role_code CHECK (code IN ('owner','manager','employee')),
	CONSTRAINT ck_tenant_role_revision CHECK (policy_revision > 0)
);


CREATE TABLE organization_memberships (
	organization_id INTEGER NOT NULL,
	identity_id INTEGER NOT NULL,
	role_code VARCHAR(16) NOT NULL,
	access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
	status VARCHAR(16) DEFAULT 'pending' NOT NULL,
	revision BIGINT DEFAULT '1' NOT NULL,
	enrollment_generation BIGINT NOT NULL,
	accepted_at TIMESTAMP WITH TIME ZONE,
	activated_at TIMESTAMP WITH TIME ZONE,
	suspended_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_organization_memberships PRIMARY KEY (id),
	CONSTRAINT ck_membership_acceptance CHECK (status != 'active' OR (accepted_at IS NOT NULL AND activated_at IS NOT NULL)),
	CONSTRAINT ck_membership_mode CHECK (access_mode IN ('company-wide','explicit-grants')),
	CONSTRAINT ck_membership_owner_scope CHECK (role_code != 'owner' OR access_mode = 'company-wide'),
	CONSTRAINT ck_membership_pending CHECK (status != 'pending' OR (accepted_at IS NULL AND activated_at IS NULL)),
	CONSTRAINT ck_membership_revision CHECK (revision > 0 AND enrollment_generation > 0),
	CONSTRAINT ck_membership_revocation CHECK (status != 'revoked' OR revoked_at IS NOT NULL),
	CONSTRAINT ck_membership_status CHECK (status IN ('pending','active','suspended','revoked')),
	CONSTRAINT ck_membership_suspension CHECK (status != 'suspended' OR suspended_at IS NOT NULL),
	CONSTRAINT fk_organization_memberships_identity_id FOREIGN KEY(identity_id) REFERENCES identities (id) ON DELETE RESTRICT,
	CONSTRAINT fk_organization_memberships_organization_id FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_organization_memberships_role_code FOREIGN KEY(role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT,
	CONSTRAINT uq_membership_actor UNIQUE (organization_id, id, identity_id),
	CONSTRAINT uq_membership_identity UNIQUE (organization_id, identity_id),
	CONSTRAINT uq_membership_mode UNIQUE (organization_id, id, access_mode)
);

CREATE INDEX ix_membership_identity_state ON organization_memberships (identity_id, status, organization_id);

CREATE INDEX ix_membership_org_role ON organization_memberships (organization_id, status, role_code);

CREATE INDEX ix_membership_role ON organization_memberships (role_code);


CREATE TABLE tenant_role_permissions (
	role_code VARCHAR(16) NOT NULL,
	permission_code VARCHAR(80) NOT NULL,
	CONSTRAINT pk_tenant_role_permissions PRIMARY KEY (role_code, permission_code),
	CONSTRAINT ck_tenant_role_permission CHECK ((role_code = 'employee' AND permission_code IN ('tenant.branches.read', 'tenant.catalog.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.read', 'tenant.restaurants.read')) OR (role_code = 'manager' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update')) OR (role_code = 'owner' AND permission_code IN ('tenant.agents.manage', 'tenant.agents.read', 'tenant.billing.checkout', 'tenant.billing.read', 'tenant.branches.manage', 'tenant.branches.read', 'tenant.catalog.manage', 'tenant.catalog.read', 'tenant.conversations.read', 'tenant.conversations.respond', 'tenant.groups.manage', 'tenant.groups.read', 'tenant.membership.self.leave', 'tenant.membership.self.read', 'tenant.memberships.manage', 'tenant.memberships.read', 'tenant.orders.fulfill', 'tenant.orders.manage', 'tenant.orders.read', 'tenant.organization.read', 'tenant.organization.suspend', 'tenant.organization.update', 'tenant.ownership.manage', 'tenant.receipts.submit', 'tenant.reports.read', 'tenant.restaurants.read', 'tenant.restaurants.update'))),
	CONSTRAINT fk_tenant_role_permissions_role_code FOREIGN KEY(role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT
);

ALTER TABLE restaurants ADD COLUMN organization_id INTEGER;

ALTER TABLE restaurant_groups ADD COLUMN organization_id INTEGER;

ALTER TABLE restaurant_branches ADD COLUMN organization_id INTEGER;

ALTER TABLE owners ADD COLUMN identity_id INTEGER;

ALTER TABLE admins ADD COLUMN identity_id INTEGER;

ALTER TABLE restaurants ADD CONSTRAINT fk_restaurants_org FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE restaurants ADD CONSTRAINT uq_restaurants_org_id UNIQUE (organization_id, id);

CREATE INDEX ix_restaurants_organization_id ON restaurants (organization_id);

ALTER TABLE restaurant_groups ADD CONSTRAINT fk_groups_org FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE restaurant_groups ADD CONSTRAINT uq_groups_org_id UNIQUE (organization_id, id);

CREATE INDEX ix_restaurant_groups_organization_id ON restaurant_groups (organization_id);

ALTER TABLE restaurant_branches ADD CONSTRAINT fk_group_link_group_org FOREIGN KEY(organization_id, group_id) REFERENCES restaurant_groups (organization_id, id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE restaurant_branches ADD CONSTRAINT fk_group_link_restaurant_org FOREIGN KEY(organization_id, restaurant_id) REFERENCES restaurants (organization_id, id) ON DELETE RESTRICT NOT VALID;

CREATE INDEX ix_group_link_org_group ON restaurant_branches (organization_id, group_id);

CREATE INDEX ix_group_link_org_restaurant ON restaurant_branches (organization_id, restaurant_id);

ALTER TABLE owners ADD CONSTRAINT fk_owner_identity FOREIGN KEY(identity_id) REFERENCES identities (id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE owners ADD CONSTRAINT uq_owner_identity UNIQUE (identity_id);

ALTER TABLE admins ADD CONSTRAINT fk_admin_identity FOREIGN KEY(identity_id) REFERENCES identities (id) ON DELETE RESTRICT NOT VALID;

ALTER TABLE admins ADD CONSTRAINT uq_admin_identity UNIQUE (identity_id);


CREATE TABLE membership_restaurant_grants (
	organization_id INTEGER NOT NULL,
	membership_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_membership_restaurant_grants PRIMARY KEY (id),
	CONSTRAINT ck_grant_mode CHECK (access_mode = 'explicit-grants'),
	CONSTRAINT fk_grant_membership FOREIGN KEY(organization_id, membership_id, access_mode) REFERENCES organization_memberships (organization_id, id, access_mode) ON DELETE RESTRICT,
	CONSTRAINT fk_grant_restaurant FOREIGN KEY(organization_id, restaurant_id) REFERENCES restaurants (organization_id, id) ON DELETE RESTRICT,
	CONSTRAINT uq_membership_restaurant UNIQUE (membership_id, restaurant_id)
);

CREATE INDEX ix_grant_membership ON membership_restaurant_grants (organization_id, membership_id, access_mode);

CREATE INDEX ix_grant_restaurant ON membership_restaurant_grants (organization_id, restaurant_id);


CREATE TABLE membership_change_proposals (
	organization_id INTEGER NOT NULL,
	target_membership_id INTEGER NOT NULL,
	target_identity_id INTEGER NOT NULL,
	actor_kind VARCHAR(16) NOT NULL,
	actor_membership_id INTEGER,
	actor_identity_id INTEGER,
	actor_admin_id INTEGER,
	proposed_role_code VARCHAR(16) NOT NULL,
	proposed_access_mode VARCHAR(20) NOT NULL,
	expected_actor_revision BIGINT,
	expected_target_revision BIGINT NOT NULL,
	enrollment_generation BIGINT NOT NULL,
	status VARCHAR(16) DEFAULT 'pending' NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	applied_at TIMESTAMP WITH TIME ZONE,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_membership_change_proposals PRIMARY KEY (id),
	CONSTRAINT ck_proposal_actor CHECK ((actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL AND expected_actor_revision IS NOT NULL AND expected_actor_revision > 0) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL AND expected_actor_revision IS NULL)),
	CONSTRAINT ck_proposal_application CHECK ((status = 'applied' AND applied_at IS NOT NULL) OR (status != 'applied' AND applied_at IS NULL)),
	CONSTRAINT ck_proposal_mode CHECK (proposed_access_mode IN ('company-wide','explicit-grants')),
	CONSTRAINT ck_proposal_owner_scope CHECK (proposed_role_code != 'owner' OR proposed_access_mode = 'company-wide'),
	CONSTRAINT ck_proposal_revision CHECK (expected_target_revision > 0 AND enrollment_generation > 0),
	CONSTRAINT ck_proposal_status CHECK (status IN ('pending','applied','cancelled','expired')),
	CONSTRAINT fk_membership_change_proposals_actor_admin_id FOREIGN KEY(actor_admin_id) REFERENCES admins (id) ON DELETE RESTRICT,
	CONSTRAINT fk_membership_change_proposals_organization_id FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_membership_change_proposals_proposed_role_code FOREIGN KEY(proposed_role_code) REFERENCES tenant_roles (code) ON DELETE RESTRICT,
	CONSTRAINT fk_proposal_actor FOREIGN KEY(organization_id, actor_membership_id, actor_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
	CONSTRAINT fk_proposal_target FOREIGN KEY(organization_id, target_membership_id, target_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
	CONSTRAINT uq_proposal_mode UNIQUE (organization_id, id, proposed_access_mode)
);

CREATE INDEX ix_proposal_actor ON membership_change_proposals (organization_id, actor_membership_id, actor_identity_id);

CREATE INDEX ix_proposal_target ON membership_change_proposals (organization_id, target_membership_id, target_identity_id);


CREATE TABLE membership_proposal_restaurants (
	organization_id INTEGER NOT NULL,
	proposal_id INTEGER NOT NULL,
	restaurant_id INTEGER NOT NULL,
	proposed_access_mode VARCHAR(20) DEFAULT 'explicit-grants' NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_membership_proposal_restaurants PRIMARY KEY (id),
	CONSTRAINT ck_proposal_restaurant_mode CHECK (proposed_access_mode = 'explicit-grants'),
	CONSTRAINT fk_proposal_restaurant_intent FOREIGN KEY(organization_id, proposal_id, proposed_access_mode) REFERENCES membership_change_proposals (organization_id, id, proposed_access_mode) ON DELETE RESTRICT,
	CONSTRAINT fk_proposal_restaurant_resource FOREIGN KEY(organization_id, restaurant_id) REFERENCES restaurants (organization_id, id) ON DELETE RESTRICT,
	CONSTRAINT uq_proposal_restaurant UNIQUE (proposal_id, restaurant_id)
);

CREATE INDEX ix_proposal_restaurant ON membership_proposal_restaurants (organization_id, restaurant_id);

CREATE INDEX ix_proposal_restaurant_parent ON membership_proposal_restaurants (organization_id, proposal_id, proposed_access_mode);


CREATE TABLE tenant_audit_events (
	organization_id INTEGER NOT NULL,
	actor_kind VARCHAR(16) NOT NULL,
	actor_membership_id INTEGER,
	actor_identity_id INTEGER,
	actor_admin_id INTEGER,
	target_membership_id INTEGER NOT NULL,
	target_identity_id INTEGER NOT NULL,
	action VARCHAR(64) NOT NULL,
	previous_revision BIGINT NOT NULL,
	resulting_revision BIGINT NOT NULL,
	enrollment_generation BIGINT NOT NULL,
	reason_code VARCHAR(64) NOT NULL,
	correlation_id VARCHAR(64) NOT NULL,
	policy_before JSON NOT NULL,
	policy_after JSON NOT NULL,
	id SERIAL NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_tenant_audit_events PRIMARY KEY (id),
	CONSTRAINT ck_audit_action CHECK (length(trim(action)) > 0),
	CONSTRAINT ck_audit_actor CHECK ((actor_kind = 'tenant' AND actor_membership_id IS NOT NULL AND actor_identity_id IS NOT NULL AND actor_admin_id IS NULL) OR (actor_kind = 'platform' AND actor_membership_id IS NULL AND actor_identity_id IS NULL AND actor_admin_id IS NOT NULL)),
	CONSTRAINT ck_audit_reason CHECK (length(trim(reason_code)) > 0 AND length(trim(correlation_id)) > 0),
	CONSTRAINT ck_audit_revisions CHECK (previous_revision > 0 AND resulting_revision > previous_revision AND enrollment_generation > 0),
	CONSTRAINT fk_audit_actor FOREIGN KEY(organization_id, actor_membership_id, actor_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
	CONSTRAINT fk_audit_target FOREIGN KEY(organization_id, target_membership_id, target_identity_id) REFERENCES organization_memberships (organization_id, id, identity_id) ON DELETE RESTRICT,
	CONSTRAINT fk_tenant_audit_events_actor_admin_id FOREIGN KEY(actor_admin_id) REFERENCES admins (id) ON DELETE RESTRICT,
	CONSTRAINT fk_tenant_audit_events_organization_id FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE RESTRICT
);

CREATE INDEX ix_audit_actor ON tenant_audit_events (organization_id, actor_membership_id, actor_identity_id);

CREATE INDEX ix_audit_target ON tenant_audit_events (organization_id, target_membership_id, target_identity_id);

INSERT INTO tenant_roles (code, policy_revision) VALUES ('employee'::VARCHAR, 1::BIGINT);

INSERT INTO tenant_roles (code, policy_revision) VALUES ('manager'::VARCHAR, 1::BIGINT);

INSERT INTO tenant_roles (code, policy_revision) VALUES ('owner'::VARCHAR, 1::BIGINT);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.branches.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.catalog.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.membership.self.leave'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.membership.self.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.orders.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('employee'::VARCHAR, 'tenant.restaurants.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.agents.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.agents.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.branches.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.branches.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.catalog.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.catalog.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.conversations.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.conversations.respond'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.groups.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.membership.self.leave'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.membership.self.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.orders.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.orders.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.organization.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.reports.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.restaurants.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('manager'::VARCHAR, 'tenant.restaurants.update'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.agents.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.agents.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.billing.checkout'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.billing.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.branches.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.branches.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.catalog.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.catalog.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.conversations.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.conversations.respond'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.groups.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.groups.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.membership.self.leave'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.membership.self.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.memberships.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.memberships.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.orders.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.orders.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.organization.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.organization.suspend'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.organization.update'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.ownership.manage'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.receipts.submit'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.reports.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.restaurants.read'::VARCHAR);

INSERT INTO tenant_role_permissions (role_code, permission_code) VALUES ('owner'::VARCHAR, 'tenant.restaurants.update'::VARCHAR);

CREATE FUNCTION public.tenant_e1_retain_record() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    RAISE EXCEPTION 'E1 retained record cannot be removed or rewritten'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_retained_record';
END;
$e1$;

CREATE FUNCTION public.tenant_e1_identity_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF ROW(NEW.id, NEW.issuer, NEW.subject, NEW.created_at)
        IS DISTINCT FROM ROW(OLD.id, OLD.issuer, OLD.subject, OLD.created_at) THEN
        RAISE EXCEPTION 'identity keys are immutable'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_immutable';
    END IF;
    IF NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION 'identity revision must advance exactly once'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_revision';
    END IF;
    IF OLD.status = 'retired' AND NEW.status <> 'retired' THEN
        RAISE EXCEPTION 'retired identity cannot be reactivated'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_identity_terminal';
    END IF;
    RETURN NEW;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_organization_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF ROW(NEW.id, NEW.created_at) IS DISTINCT FROM ROW(OLD.id, OLD.created_at)
        OR (OLD.tenant_enforced_at IS NOT NULL
            AND NEW.tenant_enforced_at IS DISTINCT FROM OLD.tenant_enforced_at) THEN
        RAISE EXCEPTION 'company identity and enforcement marker are immutable'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_immutable';
    END IF;
    IF NEW.revision <> OLD.revision + 1 THEN
        RAISE EXCEPTION 'company revision must advance exactly once'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_revision';
    END IF;
    IF OLD.status = 'archived' AND NEW.status <> 'archived' THEN
        RAISE EXCEPTION 'archived company cannot be reactivated'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_organization_terminal';
    END IF;
    RETURN NEW;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_membership_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.organization_id, NEW.identity_id, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.organization_id, OLD.identity_id, OLD.created_at) THEN
            RAISE EXCEPTION 'membership endpoints are immutable'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_immutable';
        END IF;
        IF NEW.revision <> OLD.revision + 1 THEN
            RAISE EXCEPTION 'membership revision must advance exactly once'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_revision';
        END IF;
        IF OLD.status = 'revoked' AND NEW.status <> 'revoked' THEN
            IF NEW.status <> 'pending'
                OR NEW.enrollment_generation <> OLD.enrollment_generation + 1
                OR NEW.access_mode <> 'explicit-grants'
                OR NEW.accepted_at IS NOT NULL OR NEW.activated_at IS NOT NULL
                OR NEW.suspended_at IS NOT NULL OR NEW.revoked_at IS NOT NULL
                OR EXISTS (SELECT 1 FROM public.membership_restaurant_grants
                    WHERE membership_id = OLD.id) THEN
                RAISE EXCEPTION 're-enrollment requires a fresh empty pending generation'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_enrollment';
            END IF;
        ELSIF NEW.enrollment_generation <> OLD.enrollment_generation THEN
            RAISE EXCEPTION 'enrollment generation is immutable outside re-enrollment'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_membership_generation';
        END IF;
    END IF;
    -- A real company-row write serializes competing owner reductions. Merely
    -- locking that row at deferred-check time is insufficient under snapshot isolation.
    -- Writing the identity, rather than only sharing its lock, also serializes
    -- status changes against memberships invisible to an older RR snapshot.
    -- REPEATABLE READ / SERIALIZABLE writers must retry on 40001. Contexts must
    -- be resolved again after this deliberately conservative revision advance.
    UPDATE public.identities SET revision = revision + 1, updated_at = now()
        WHERE id = NEW.identity_id;
    UPDATE public.organizations SET revision = revision + 1, updated_at = now()
        WHERE id = NEW.organization_id;
    RETURN NEW;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_identity_companies() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE company_id integer;
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        FOR company_id IN SELECT DISTINCT organization_id
            FROM public.organization_memberships WHERE identity_id = NEW.id
            ORDER BY organization_id
        LOOP
            UPDATE public.organizations SET revision = revision + 1, updated_at = now()
                WHERE id = company_id;
        END LOOP;
    END IF;
    RETURN NULL;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_assert_owner(company_id integer) RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE company_state text;
BEGIN
    SELECT status INTO company_state FROM public.organizations
        WHERE id = company_id FOR UPDATE;
    -- Separate statement: at READ COMMITTED this obtains a fresh snapshot after
    -- serialization. The earlier revision write forces a conflict at higher levels.
    IF company_state = 'active' AND NOT EXISTS (
        SELECT 1 FROM public.organization_memberships AS m
        JOIN public.identities AS i ON i.id = m.identity_id
        WHERE m.organization_id = company_id AND m.role_code = 'owner'
          AND m.status = 'active' AND m.access_mode = 'company-wide'
          AND m.accepted_at IS NOT NULL AND m.activated_at IS NOT NULL
          AND i.status = 'active'
    ) THEN
        RAISE EXCEPTION 'active company requires a qualifying active owner'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_organization_active_owner';
    END IF;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_owner_deferred() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    IF TG_TABLE_NAME = 'organizations' THEN
        PERFORM public.tenant_e1_assert_owner(NEW.id);
    ELSE
        PERFORM public.tenant_e1_assert_owner(NEW.organization_id);
    END IF;
    RETURN NULL;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_assignment_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
DECLARE old_key integer; new_key integer; company_state text; enforcement timestamptz;
BEGIN
    IF TG_TABLE_NAME IN ('owners', 'admins') THEN
        IF TG_OP <> 'INSERT' THEN old_key := OLD.identity_id; END IF;
        IF TG_OP <> 'DELETE' THEN new_key := NEW.identity_id; END IF;
    ELSE
        IF TG_OP <> 'INSERT' THEN old_key := OLD.organization_id; END IF;
        IF TG_OP <> 'DELETE' THEN new_key := NEW.organization_id; END IF;
    END IF;
    -- Untagged legacy rows retain their existing behavior throughout expansion.
    IF old_key IS NOT NULL THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'linked resource must retain its historical identity'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_retained';
        END IF;
        IF new_key IS DISTINCT FROM old_key OR NEW.id IS DISTINCT FROM OLD.id THEN
            RAISE EXCEPTION 'resource assignment is immutable'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_immutable';
        END IF;
        IF TG_TABLE_NAME = 'restaurant_branches' THEN
            IF ROW(NEW.group_id, NEW.restaurant_id)
                IS DISTINCT FROM ROW(OLD.group_id, OLD.restaurant_id) THEN
                RAISE EXCEPTION 'linked group endpoints are immutable'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_group_link_immutable';
            END IF;
        END IF;
    ELSIF new_key IS NOT NULL AND TG_TABLE_NAME NOT IN ('owners', 'admins') THEN
        SELECT status, tenant_enforced_at INTO company_state, enforcement
            FROM public.organizations WHERE id = new_key FOR SHARE;
        IF company_state IS DISTINCT FROM 'draft' OR enforcement IS NOT NULL THEN
            RAISE EXCEPTION 'E1 assignment requires a draft unenforced company'
                USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_assignment_staged';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$e1$;

CREATE FUNCTION public.tenant_e1_closed_policy() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $e1$
BEGIN
    -- E1 does not release acceptance/sealing or tenant-facing policy editing.
    -- A separately reviewed revision must replace this fence with the complete
    -- immutable proposal-graph and accepted-governance contract before use.
    RAISE EXCEPTION 'E1 governance and policy mutation are closed pending separate review'
        USING ERRCODE = '23514', CONSTRAINT = 'ck_e1_governance_closed';
END;
$e1$;

CREATE TRIGGER tr_e1_identity_guard BEFORE UPDATE ON public.identities FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_identity_guard();

CREATE TRIGGER tr_e1_identity_companies AFTER UPDATE ON public.identities FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_identity_companies();

CREATE TRIGGER tr_e1_organization_guard BEFORE UPDATE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_organization_guard();

CREATE TRIGGER tr_e1_membership_guard BEFORE INSERT OR UPDATE ON public.organization_memberships FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_membership_guard();

CREATE CONSTRAINT TRIGGER ct_e1_organization_owner AFTER INSERT OR UPDATE ON public.organizations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_owner_deferred();

CREATE CONSTRAINT TRIGGER ct_e1_membership_owner AFTER INSERT OR UPDATE ON public.organization_memberships DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_owner_deferred();

CREATE TRIGGER tr_e1_identities_retain BEFORE DELETE ON public.identities FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_organizations_retain BEFORE DELETE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_organization_memberships_retain BEFORE DELETE ON public.organization_memberships FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_audit_retain BEFORE UPDATE OR DELETE ON public.tenant_audit_events FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_identities_truncate BEFORE TRUNCATE ON public.identities FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_organizations_truncate BEFORE TRUNCATE ON public.organizations FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_tenant_roles_truncate BEFORE TRUNCATE ON public.tenant_roles FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_tenant_role_permissions_truncate BEFORE TRUNCATE ON public.tenant_role_permissions FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_organization_memberships_truncate BEFORE TRUNCATE ON public.organization_memberships FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_membership_restaurant_grants_truncate BEFORE TRUNCATE ON public.membership_restaurant_grants FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_membership_change_proposals_truncate BEFORE TRUNCATE ON public.membership_change_proposals FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_membership_proposal_restaurants_truncate BEFORE TRUNCATE ON public.membership_proposal_restaurants FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_tenant_audit_events_truncate BEFORE TRUNCATE ON public.tenant_audit_events FOR EACH STATEMENT EXECUTE FUNCTION public.tenant_e1_retain_record();

CREATE TRIGGER tr_e1_restaurants_assignment BEFORE INSERT OR UPDATE OR DELETE ON public.restaurants FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard();

CREATE TRIGGER tr_e1_restaurant_groups_assignment BEFORE INSERT OR UPDATE OR DELETE ON public.restaurant_groups FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard();

CREATE TRIGGER tr_e1_restaurant_branches_assignment BEFORE INSERT OR UPDATE OR DELETE ON public.restaurant_branches FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard();

CREATE TRIGGER tr_e1_owners_assignment BEFORE INSERT OR UPDATE OR DELETE ON public.owners FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard();

CREATE TRIGGER tr_e1_admins_assignment BEFORE INSERT OR UPDATE OR DELETE ON public.admins FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_assignment_guard();

CREATE TRIGGER tr_e1_tenant_roles_closed BEFORE INSERT OR UPDATE OR DELETE ON public.tenant_roles FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_closed_policy();

CREATE TRIGGER tr_e1_tenant_role_permissions_closed BEFORE INSERT OR UPDATE OR DELETE ON public.tenant_role_permissions FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_closed_policy();

CREATE TRIGGER tr_e1_membership_change_proposals_closed BEFORE INSERT OR UPDATE OR DELETE ON public.membership_change_proposals FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_closed_policy();

CREATE TRIGGER tr_e1_membership_proposal_restaurants_closed BEFORE INSERT OR UPDATE OR DELETE ON public.membership_proposal_restaurants FOR EACH ROW EXECUTE FUNCTION public.tenant_e1_closed_policy();

REVOKE ALL ON TABLE public.identities FROM PUBLIC;

REVOKE ALL ON TABLE public.organizations FROM PUBLIC;

REVOKE ALL ON TABLE public.tenant_roles FROM PUBLIC;

REVOKE ALL ON TABLE public.organization_memberships FROM PUBLIC;

REVOKE ALL ON TABLE public.tenant_role_permissions FROM PUBLIC;

REVOKE ALL ON TABLE public.membership_restaurant_grants FROM PUBLIC;

REVOKE ALL ON TABLE public.membership_change_proposals FROM PUBLIC;

REVOKE ALL ON TABLE public.membership_proposal_restaurants FROM PUBLIC;

REVOKE ALL ON TABLE public.tenant_audit_events FROM PUBLIC;

UPDATE alembic_version SET version_num='e1a92b200001' WHERE alembic_version.version_num = 'c413b7918a20';

ALTER TABLE subscriptions ADD COLUMN calendar_anchor TIMESTAMP, ADD COLUMN cancelled_at TIMESTAMP, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD', ADD COLUMN market VARCHAR(10);

ALTER TABLE subscriptions ALTER COLUMN amount TYPE NUMERIC(24,8) USING amount::numeric;

ALTER TABLE payments ALTER COLUMN amount TYPE NUMERIC(24,8) USING amount::numeric;

ALTER TABLE feature_pricing ALTER COLUMN price TYPE NUMERIC(24,8) USING price::numeric, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD';

ALTER TABLE branch_pricing ALTER COLUMN price_per_branch TYPE NUMERIC(24,8) USING price_per_branch::numeric, ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'DZD', ADD COLUMN market VARCHAR(10), ADD COLUMN grid_code VARCHAR(80) NOT NULL DEFAULT 'legacy-review-required', ADD COLUMN starts_at TIMESTAMP, ADD COLUMN expires_at TIMESTAMP;

UPDATE branch_pricing SET active=false;

INSERT INTO branch_pricing(min_branches,max_branches,price_per_branch,active,currency,grid_code) VALUES(2,5,500,true,'DZD','approved-dzd-20261029'),(6,20,400,true,'DZD','approved-dzd-20261029'),(21,NULL,300,true,'DZD','approved-dzd-20261029');

ALTER TABLE loyalty_discounts ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric;

ALTER TABLE multi_restaurant_discounts ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric;

ALTER TABLE promotions ALTER COLUMN discount_percent TYPE NUMERIC(12,8) USING discount_percent::numeric, ADD COLUMN owner_id INTEGER REFERENCES owners(id), ADD COLUMN plan_id INTEGER REFERENCES subscription_plans(id), ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;

CREATE TABLE subscription_reminders(id SERIAL PRIMARY KEY, subscription_id INTEGER NOT NULL REFERENCES subscriptions(id), expires_at TIMESTAMP NOT NULL, offset_days INTEGER NOT NULL CHECK(offset_days>=0), recipient VARCHAR(30) NOT NULL, target_chat_id VARCHAR(40), due_at TIMESTAMP NOT NULL, status VARCHAR(20) NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, sent_at TIMESTAMP, attempt_log JSON NOT NULL DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CONSTRAINT uq_subscription_reminder UNIQUE(subscription_id,expires_at,offset_days,recipient));

ALTER TABLE subscription_features ADD CONSTRAINT uq_subscription_feature UNIQUE(subscription_id,feature_id);

ALTER TABLE subscription_feature_requests ADD CONSTRAINT uq_subscription_feature_request UNIQUE(subscription_id,feature_id);

CREATE TABLE subscription_pricing_config (
      id INTEGER PRIMARY KEY CHECK (id=1), base_price NUMERIC(14,2) NOT NULL CHECK(base_price>=0),
      policies JSON NOT NULL DEFAULT '{}', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

INSERT INTO subscription_pricing_config(id,base_price,policies) VALUES(1,3000,'{"currencies":{"DZD":{"decimals":2}},"reminder_days":[14,7,1,0]}');

CREATE TABLE subscription_pricing_snapshots (
      id SERIAL PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES owners(id),
      restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
      subscription_id INTEGER UNIQUE REFERENCES subscriptions(id),
      source_subscription_id INTEGER NOT NULL REFERENCES subscriptions(id),
      reference_start TIMESTAMP NOT NULL, reference_end TIMESTAMP NOT NULL,
      context VARCHAR(30) NOT NULL, products_count INTEGER NOT NULL CHECK(products_count>=0),
      categories_count INTEGER NOT NULL CHECK(categories_count>=0),
      monthly_orders INTEGER NOT NULL CHECK(monthly_orders>=0),
      average_order_value NUMERIC(20,8) NOT NULL CHECK(average_order_value>=0 AND average_order_value::text NOT IN ('NaN','Infinity','-Infinity')),
      calculated_at TIMESTAMP NOT NULL, pricing JSON NOT NULL, parameters JSON NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT ck_snapshot_period CHECK(reference_end-reference_start=INTERVAL '30 days'),
      CONSTRAINT ck_snapshot_context CHECK(context IN ('active_month','trial_end','renewal','return')));

CREATE UNIQUE INDEX uq_subscription_metric_period ON subscription_pricing_snapshots(source_subscription_id,reference_end) WHERE context='active_month' AND subscription_id IS NULL;

CREATE FUNCTION moulai_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'subscription_snapshot_immutable'; END IF;
      IF NOT EXISTS(SELECT 1 FROM restaurants WHERE id=NEW.restaurant_id AND owner_id=NEW.owner_id)
        THEN RAISE EXCEPTION 'snapshot_owner_mismatch'; END IF;
      IF NEW.subscription_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM subscriptions
        WHERE id=NEW.subscription_id AND owner_id=NEW.owner_id AND restaurant_id=NEW.restaurant_id)
        THEN RAISE EXCEPTION 'snapshot_subscription_mismatch'; END IF;
      IF NEW.source_subscription_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM subscriptions
        WHERE id=NEW.source_subscription_id AND owner_id=NEW.owner_id AND restaurant_id=NEW.restaurant_id)
        THEN RAISE EXCEPTION 'snapshot_source_mismatch'; END IF;
      RETURN NEW;
    END $$;

CREATE TRIGGER subscription_snapshot_guard BEFORE INSERT OR UPDATE OR DELETE ON subscription_pricing_snapshots FOR EACH ROW EXECUTE FUNCTION moulai_snapshot_guard();

CREATE FUNCTION moulai_retained_price_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM subscription_pricing_snapshots WHERE subscription_id=OLD.id) THEN
        IF (NEW.amount,NEW.currency,NEW.plan_id,NEW.billing_cycle,NEW.owner_id,NEW.restaurant_id)
           IS DISTINCT FROM (OLD.amount,OLD.currency,OLD.plan_id,OLD.billing_cycle,OLD.owner_id,OLD.restaurant_id)
          THEN RAISE EXCEPTION 'retained_subscription_price_immutable'; END IF;
        IF OLD.starts_at IS NOT NULL AND (NEW.starts_at,NEW.expires_at,NEW.calendar_anchor)
           IS DISTINCT FROM (OLD.starts_at,OLD.expires_at,OLD.calendar_anchor)
          THEN RAISE EXCEPTION 'purchased_subscription_period_immutable'; END IF;
      END IF;
      RETURN NEW;
    END $$;

CREATE TRIGGER retained_subscription_price BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION moulai_retained_price_guard();

CREATE TABLE cash_collections (
      id SERIAL PRIMARY KEY, payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(id),
      subscription_id INTEGER NOT NULL REFERENCES subscriptions(id), admin_id INTEGER NOT NULL REFERENCES admins(id),
      expected_amount NUMERIC(24,8) NOT NULL CHECK(expected_amount>0),
      received_amount NUMERIC(24,8) NOT NULL CHECK(received_amount=expected_amount),
      currency VARCHAR(3) NOT NULL, collected_at TIMESTAMP NOT NULL, confirmed_at TIMESTAMP NOT NULL,
      receipt_reference VARCHAR(120) NOT NULL UNIQUE,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE cash_collection_attempts (
      id SERIAL PRIMARY KEY, attempt_id VARCHAR(32) NOT NULL, payment_id INTEGER NOT NULL,
      attempted_admin_id INTEGER NOT NULL, result VARCHAR(40) NOT NULL, details JSON NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE INDEX ix_cash_collection_attempts_attempt_id ON cash_collection_attempts(attempt_id);

INSERT INTO permissions(code,name) VALUES('payments.cash.collect','Confirm physical cash collection') ON CONFLICT(code) DO NOTHING;

CREATE FUNCTION moulai_cash_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'cash_evidence_immutable'; END IF;
      IF TG_TABLE_NAME='cash_collections' THEN
        IF NOT EXISTS(SELECT 1 FROM payments p JOIN subscriptions s ON s.id=p.subscription_id
          WHERE p.id=NEW.payment_id AND p.subscription_id=NEW.subscription_id
            AND p.payment_method='cash' AND p.payment_provider='manual_cash' AND p.status='pending'
            AND p.amount=NEW.expected_amount AND p.currency=NEW.currency
            AND s.amount=p.amount AND s.currency=p.currency AND s.owner_id=p.owner_id AND s.restaurant_id=p.restaurant_id)
          THEN RAISE EXCEPTION 'cash_payment_terms_mismatch'; END IF;
        IF NEW.collected_at>NEW.confirmed_at THEN RAISE EXCEPTION 'cash_date_invalid'; END IF;
      END IF;
      RETURN NEW;
    END $$;

CREATE TRIGGER cash_evidence_guard BEFORE INSERT OR UPDATE OR DELETE ON cash_collections FOR EACH ROW EXECUTE FUNCTION moulai_cash_evidence_guard();

CREATE TRIGGER cash_attempt_guard BEFORE INSERT OR UPDATE OR DELETE ON cash_collection_attempts FOR EACH ROW EXECUTE FUNCTION moulai_cash_evidence_guard();

CREATE FUNCTION moulai_cash_payment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM cash_collections WHERE payment_id=OLD.id) AND
        (NEW.amount,NEW.currency,NEW.subscription_id,NEW.owner_id,NEW.restaurant_id,NEW.payment_method,NEW.payment_provider)
        IS DISTINCT FROM (OLD.amount,OLD.currency,OLD.subscription_id,OLD.owner_id,OLD.restaurant_id,OLD.payment_method,OLD.payment_provider)
        THEN RAISE EXCEPTION 'cash_payment_terms_immutable'; END IF;
      RETURN NEW;
    END $$;

CREATE TRIGGER cash_payment_guard BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION moulai_cash_payment_guard();

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 1,2 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=1 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 2,5 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=2 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 3,8 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=3 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 4,11 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=4 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 5,15 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=5 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 10,20 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=10 AND owner_id IS NULL);

INSERT INTO loyalty_discounts(years_required,discount_percent) SELECT 15,25 WHERE NOT EXISTS(SELECT 1 FROM loyalty_discounts WHERE years_required=15 AND owner_id IS NULL);

INSERT INTO multi_restaurant_discounts(min_restaurants,discount_percent) SELECT 1,0 WHERE NOT EXISTS(SELECT 1 FROM multi_restaurant_discounts WHERE min_restaurants=1);

INSERT INTO multi_restaurant_discounts(min_restaurants,discount_percent) SELECT 3,5 WHERE NOT EXISTS(SELECT 1 FROM multi_restaurant_discounts WHERE min_restaurants=3);

INSERT INTO multi_restaurant_discounts(min_restaurants,discount_percent) SELECT 10,15 WHERE NOT EXISTS(SELECT 1 FROM multi_restaurant_discounts WHERE min_restaurants=10);

UPDATE alembic_version SET version_num='s1a20261028' WHERE alembic_version.version_num = 'e1a92b200001';
