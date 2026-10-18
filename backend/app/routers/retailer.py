"""Retailer endpoints (SPEC §8): product CRUD, pool view, notifications. Launch and demand are still TODO."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import retailer_user
from app.errors import not_found
from app.models import Pool, Product, User
from app.schemas import NotificationList, ProductCreate, ProductUpdate, RetailerPoolDetail, RetailerProduct
from app.services import catalog, notifications, pool_engine, views

router = APIRouter(prefix="/retailer", dependencies=[Depends(retailer_user)])


@router.get("/products", response_model=list[RetailerProduct])
def list_products(user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    products = session.exec(
        select(Product).where(Product.retailer_id == user.retailer_id).order_by(Product.id)
    ).all()
    for product in products:
        pool = views.latest_pool(session, product)
        if pool is not None:
            pool_engine.evaluate_pool(session, pool)
    return [views.retailer_product(session, p) for p in products]


@router.post("/products", response_model=RetailerProduct)
def create_product(body: ProductCreate, user: User = Depends(retailer_user),
                   session: Session = Depends(get_session)):
    return views.retailer_product(session, catalog.create_product(session, user, body))


@router.patch("/products/{product_id}", response_model=RetailerProduct)
def update_product(product_id: int, body: ProductUpdate, user: User = Depends(retailer_user),
                   session: Session = Depends(get_session)):
    product = catalog.get_own_product(session, user, product_id)
    return views.retailer_product(session, catalog.update_product(session, product, body))


@router.get("/pools/{pool_id}", response_model=RetailerPoolDetail)
def retailer_pool(pool_id: int, user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    pool = session.get(Pool, pool_id)
    product = session.get(Product, pool.product_id) if pool else None
    if product is None or product.retailer_id != user.retailer_id:
        raise not_found("Pool")
    pool = pool_engine.evaluate_pool(session, pool)
    return views.retailer_pool_detail(session, pool)


@router.get("/notifications", response_model=NotificationList)
def retailer_notifications(user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    return notifications.list_for(session, user.id)
