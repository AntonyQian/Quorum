"""Retailer endpoints (SPEC §8): product CRUD, launch, demand, pool view. TODO."""

from fastapi import APIRouter, Depends

from app.deps import retailer_user

router = APIRouter(prefix="/retailer", dependencies=[Depends(retailer_user)])
