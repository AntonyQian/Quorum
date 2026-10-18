"""Retailer endpoints (SPEC §8): product CRUD, Launch, demand stats, pool view, notifications."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import retailer_user
from app.models import User
from app.schemas import NotificationList, PoolCreate, PoolDetail, ProductCreate, ProductDemand, ProductUpdate, RetailerPoolDetail, RetailerProduct
from app.services import catalog, notifications, pool_engine, views

router = APIRouter(prefix="/retailer", dependencies=[Depends(retailer_user)])


@router.get("/products", response_model=list[RetailerProduct])
def list_products(user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    return [views.retailer_product(session, p) for p in catalog.list_products(session, user)]


@router.post("/products", response_model=RetailerProduct)
def create_product(body: ProductCreate, user: User = Depends(retailer_user),
                   session: Session = Depends(get_session)):
    return views.retailer_product(session, catalog.create_product(session, user, body))


@router.patch("/products/{product_id}", response_model=RetailerProduct)
def update_product(product_id: int, body: ProductUpdate, user: User = Depends(retailer_user),
                   session: Session = Depends(get_session)):
    product = catalog.get_own_product(session, user, product_id)
    return views.retailer_product(session, catalog.update_product(session, product, body))


@router.delete("/products/{product_id}")
def delete_product(product_id: int, user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    catalog.delete_product(session, catalog.get_own_product(session, user, product_id))
    return {"ok": True}


@router.post("/products/{product_id}/launch", response_model=PoolDetail)
def launch_product(product_id: int, body: PoolCreate, user: User = Depends(retailer_user),
                   session: Session = Depends(get_session)):
    product = catalog.get_own_product(session, user, product_id)
    return views.pool_detail(session, catalog.launch(session, product, body), None)


@router.get("/products/{product_id}/demand", response_model=ProductDemand)
def product_demand(product_id: int, user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    return views.product_demand(session, catalog.get_own_product(session, user, product_id))


@router.get("/pools/{pool_id}", response_model=RetailerPoolDetail)
def retailer_pool(pool_id: int, user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    pool = pool_engine.evaluate_pool(session, catalog.get_own_pool(session, user, pool_id))
    return views.retailer_pool_detail(session, pool)


@router.get("/notifications", response_model=NotificationList)
def retailer_notifications(user: User = Depends(retailer_user), session: Session = Depends(get_session)):
    return notifications.list_for(session, user.id)
