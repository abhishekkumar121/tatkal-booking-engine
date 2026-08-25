"""create initial tables

Revision ID: 7eb15e398194
Revises:
Create Date: 2026-07-23 16:29:26.052145

"""

# Type hints ke liye Sequence aur Union import kar rahe hain.
from typing import Sequence, Union

# Alembic operations helper; create_table/drop_table jaise commands isi se chalenge.
from alembic import op

# SQLAlchemy ko sa alias kar rahe hain taaki column types define kar sakein.
import sqlalchemy as sa


# Ye migration ka unique revision id hai.
revision: str = '7eb15e398194'

# Is migration se pehle koi migration nahi thi, isliye None.
down_revision: Union[str, Sequence[str], None] = None

# Branch labels advanced Alembic feature hai; yahan use nahi ho raha.
branch_labels: Union[str, Sequence[str], None] = None

# Agar ye migration kisi aur migration par depend karti, to yahan aata; abhi None.
depends_on: Union[str, Sequence[str], None] = None


# upgrade database schema ko aage/latest version par le jaata hai.
def upgrade() -> None:
    # Docstring batata hai function schema upgrade karta hai.
    """Upgrade schema."""
    # Products table create kar rahe hain.
    op.create_table('products',
    # Product id column; integer aur required.
    sa.Column('id', sa.Integer(), nullable=False),
    # Product name column; max 255 characters aur required.
    sa.Column('name', sa.String(length=255), nullable=False),
    # Product price column; total 10 digits, 2 decimal places.
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    # Product total stock column; required integer.
    sa.Column('total_stock', sa.Integer(), nullable=False),
    # Product created_at column; default database current time.
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    # id ko primary key set kar rahe hain.
    sa.PrimaryKeyConstraint('id')
    )
    # products.id par index create kar rahe hain for faster lookup.
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    # Users table create kar rahe hain.
    op.create_table('users',
    # User id column; integer aur required.
    sa.Column('id', sa.Integer(), nullable=False),
    # User email column; max 255 characters aur required.
    sa.Column('email', sa.String(length=255), nullable=False),
    # Hashed password column; required.
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    # User created_at column; default database current time.
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    # id ko primary key set kar rahe hain.
    sa.PrimaryKeyConstraint('id'),
    # email unique hona chahiye.
    sa.UniqueConstraint('email')
    )
    # users.id par index create kar rahe hain.
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    # Flash sales table create kar rahe hain.
    op.create_table('flash_sales',
    # Flash sale id column.
    sa.Column('id', sa.Integer(), nullable=False),
    # Product id column; products table se link hoga.
    sa.Column('product_id', sa.Integer(), nullable=True),
    # Sale start time column.
    sa.Column('start_time', sa.TIMESTAMP(), nullable=False),
    # Sale end time column.
    sa.Column('end_time', sa.TIMESTAMP(), nullable=False),
    # Per user maximum quantity column.
    sa.Column('max_per_user', sa.Integer(), nullable=True),
    # Sale status column.
    sa.Column('status', sa.String(length=20), nullable=True),
    # Flash sale created_at column.
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    # product_id ko products.id se foreign key banate hain.
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    # id ko primary key set karte hain.
    sa.PrimaryKeyConstraint('id')
    )
    # flash_sales.id par index create karte hain.
    op.create_index(op.f('ix_flash_sales_id'), 'flash_sales', ['id'], unique=False)
    # Orders table create kar rahe hain.
    op.create_table('orders',
    # Order id column.
    sa.Column('id', sa.Integer(), nullable=False),
    # User id column; users table se link hoga.
    sa.Column('user_id', sa.Integer(), nullable=True),
    # Flash sale id column; flash_sales table se link hoga.
    sa.Column('flash_sale_id', sa.Integer(), nullable=True),
    # Quantity column.
    sa.Column('quantity', sa.Integer(), nullable=True),
    # Order status column.
    sa.Column('status', sa.String(length=20), nullable=True),
    # Duplicate order prevent karne ke liye unique idempotency key.
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    # Order created_at column.
    sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=True),
    # flash_sale_id ko flash_sales.id se foreign key banate hain.
    sa.ForeignKeyConstraint(['flash_sale_id'], ['flash_sales.id'], ),
    # user_id ko users.id se foreign key banate hain.
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    # id ko primary key set karte hain.
    sa.PrimaryKeyConstraint('id'),
    # idempotency_key unique hona chahiye.
    sa.UniqueConstraint('idempotency_key')
    )
    # orders.id par index create karte hain.
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)


# downgrade database schema ko previous version par wapas le jaata hai.
def downgrade() -> None:
    # Docstring batata hai function schema downgrade karta hai.
    """Downgrade schema."""
    # Orders id index drop karte hain.
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    # Orders table drop karte hain.
    op.drop_table('orders')
    # Flash sales id index drop karte hain.
    op.drop_index(op.f('ix_flash_sales_id'), table_name='flash_sales')
    # Flash sales table drop karte hain.
    op.drop_table('flash_sales')
    # Users id index drop karte hain.
    op.drop_index(op.f('ix_users_id'), table_name='users')
    # Users table drop karte hain.
    op.drop_table('users')
    # Products id index drop karte hain.
    op.drop_index(op.f('ix_products_id'), table_name='products')
    # Products table drop karte hain.
    op.drop_table('products')
