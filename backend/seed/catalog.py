"""The hard-coded starter catalog: every Product the demo database starts with.

Prices are integer cents. `floor_price_cents` is the lowest price the Retailer will allow, so every Tier
discount must satisfy list - discount >= floor. Photos are Unsplash furniture shots that match the product.

- `pool(...)` makes a public Product with a live Pool: `fill` Members have already joined, `late_fill` more
  join after the Pool Locks, and `settle=True` runs the Deadline so Tier Refunds are issued.
- `hidden(...)` makes a Hidden Listing that has `hits` of its `threshold` Demand Hits.
"""

from typing import Any

OAK = "Oak & Co."
NORDLUND = "Nordlund"
RELOFT = "ReLoft"

RETAILERS = [
    {"name": OAK, "tagline": "Solid wood, built to last"},
    {"name": NORDLUND, "tagline": "Modern Scandinavian living"},
    {"name": RELOFT, "tagline": "Refurbished furniture, like new"},
]

SHOPPERS = ["Alice", "Bob", "Casey"]
ADMIN_NAME = "Quorum Admin"
SIMULATED_SHOPPER_COUNT = 40
DECLINING_SHOPPER_NAME = "Sim Dana"

_IMAGE_SUFFIX = "?auto=format&fit=crop&w=1200&q=80"


def _product(
    retailer: str,
    name: str,
    category: str,
    photo: str,
    description: str,
    tags: list[str],
    dimensions: str,
    list_price: int,
    floor_price: int,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "retailer": retailer,
        "name": name,
        "category": category,
        "description": description,
        "style_tags": tags,
        "dimensions": dimensions,
        "list_price_cents": list_price,
        "floor_price_cents": floor_price,
        "image_url": f"https://images.unsplash.com/photo-{photo}{_IMAGE_SUFFIX}",
        **extra,
    }


def pool(days: int, fill: int, tiers: list[tuple[int, int]], late_fill: int = 0, settle: bool = False) -> dict[str, Any]:
    spec: dict[str, Any] = {"deadline_days": days, "fill": fill, "tiers": tiers}
    if late_fill:
        spec["late_fill"] = late_fill
    if settle:
        spec["settle"] = True
    return {"pool": spec}


def hidden(threshold: int, hits: int) -> dict[str, Any]:
    return {"hidden": {"demand_threshold": threshold, "hits": hits}}


PRODUCTS: list[dict[str, Any]] = [
    # --- Sofas ---
    _product(NORDLUND, "Moss Green Sofa", "sofa", "1555041469-a586c61ea9bc",
             "Three-seat sofa in soft moss green woven fabric.", ["scandinavian", "green", "fabric"],
             "210 x 90 x 80 cm", 129900, 99900, **pool(21, 12, [(10, 15000), (25, 30000)])),
    _product(RELOFT, "Tan Leather Loveseat", "sofa", "1512212621149-107ffe572d2f",
             "Two-seat leather loveseat, cleaned and conditioned.", ["leather", "tan", "refurbished"],
             "158 x 88 x 82 cm", 89900, 71900, **pool(12, 4, [(6, 9000), (15, 18000)])),
    _product(RELOFT, "Leather Chesterfield", "sofa", "1573866926487-a1865558a9cf",
             "Deep-buttoned brown leather Chesterfield, professionally restored.", ["leather", "brown", "traditional"],
             "205 x 92 x 78 cm", 149900, 119900, **pool(5, 6, [(5, 15000), (12, 30000)])),
    _product(NORDLUND, "Slate Three-Seat Sofa", "sofa", "1698936061086-2bf99c7b9fc5",
             "Grey three-seat sofa with four scatter cushions.", ["scandinavian", "grey", "fabric"],
             "216 x 92 x 84 cm", 109900, 87900, **pool(16, 3, [(8, 11000), (20, 22000)])),
    _product(RELOFT, "Cognac Leather Sofa", "sofa", "1691480152351-4b3f2c89ccff",
             "Full-grain cognac leather sofa with a slim track arm.", ["leather", "cognac", "modern"],
             "224 x 94 x 80 cm", 179900, 139900, **pool(9, 4, [(6, 20000), (14, 40000)])),
    _product(NORDLUND, "Cloud Bouclé Sofa", "sofa", "1684165610413-2401399e0e59",
             "Low, rounded sofa upholstered in cream bouclé.", ["boucle", "cream", "modern"],
             "200 x 95 x 70 cm", 139900, 111900, **hidden(10, 4)),
    _product(NORDLUND, "Forest Velvet Sofa", "sofa", "1590251024078-8a6d9f90b02d",
             "Dark green velvet sofa with two striped cushions.", ["velvet", "green", "statement"],
             "204 x 90 x 78 cm", 119900, 95900, **pool(24, 1, [(8, 12000), (18, 24000)])),

    # --- Seating ---
    _product(RELOFT, "Tufted Leather Armchair", "seating", "1567538096630-e0c55bd6374c",
             "Mid-century tufted white leather armchair, professionally restored.", ["leather", "mid-century", "white"],
             "75 x 80 x 85 cm", 64900, 51900, **pool(2, 3, [(5, 6500), (12, 13000)])),
    _product(OAK, "Oak Frame Lounge Chair", "seating", "1580480055273-228ff5388ef8",
             "Solid oak frame with a grey padded seat and back.", ["oak", "grey", "scandinavian"],
             "68 x 76 x 80 cm", 45900, 36900, **pool(13, 5, [(6, 4500), (15, 9000)])),
    _product(RELOFT, "Mustard Mid-Century Chair", "seating", "1586023492125-27b2c045efd7",
             "Mustard padded chair on a wooden frame, reupholstered.", ["mid-century", "mustard", "refurbished"],
             "64 x 70 x 78 cm", 37900, 29900, **pool(8, 2, [(5, 4000), (12, 8000)])),
    _product(OAK, "Walnut Accent Armchair", "seating", "1617364852223-75f57e78dc96",
             "Black padded armchair on a sculpted walnut frame.", ["walnut", "black", "mid-century"],
             "66 x 72 x 82 cm", 54900, 43900, **pool(15, 3, [(6, 5500), (14, 11000)])),
    _product(NORDLUND, "Teak Lounge Chair", "seating", "1605702098590-d552a98dc93d",
             "Open-arm teak lounge chair with a low reclined back.", ["teak", "scandinavian", "lounge"],
             "62 x 78 x 74 cm", 51900, 31900, **pool(7, 14, [(5, 5000), (12, 12000), (25, 20000)])),
    _product(NORDLUND, "Round Bouclé Armchair", "seating", "1759722667456-71e7bfd118b2",
             "Round upholstered armchair with a deep, hugging seat.", ["boucle", "cream", "modern"],
             "78 x 74 x 76 cm", 59900, 47900, **pool(14, 7, [(6, 6000), (14, 12000)])),
    _product(RELOFT, "Vintage Leather Club Chair", "seating", "1601366533287-5ee4c763ae4e",
             "Brown leather club chair with a worn-in patina, restored.", ["leather", "brown", "vintage"],
             "82 x 84 x 78 cm", 68900, 55900, **hidden(10, 2)),

    # --- Dining ---
    _product(OAK, "Farmhouse Dining Set", "dining_table", "1617806118233-18e1de247200",
             "Painted-leg oak table with four matching chairs.", ["oak", "farmhouse", "painted"],
             "160 x 90 x 76 cm", 119900, 95900, **pool(10, 8, [(10, 12000), (20, 24000)])),
    _product(OAK, "Walnut Dining Table", "dining_table", "1505409628601-edc9af17fda6",
             "Solid walnut dining table that seats four to six.", ["walnut", "mid-century"],
             "150 x 85 x 75 cm", 89900, 59900, **hidden(10, 9)),
    _product(OAK, "Oak Trestle Dining Table", "dining_table", "1604578762246-41134e37f9cc",
             "Solid oak trestle table with a hand-oiled finish.", ["oak", "trestle", "traditional"],
             "180 x 90 x 75 cm", 104900, 83900, **pool(19, 4, [(8, 10500), (18, 21000)])),
    _product(OAK, "Six-Seat Oak Dining Set", "dining_table", "1758977404039-6e834be8eca8",
             "Oak dining table with six upholstered chairs.", ["oak", "upholstered", "family"],
             "200 x 95 x 76 cm", 159900, 127900, **pool(6, 6, [(6, 16000), (14, 32000)])),
    _product(NORDLUND, "White Ash Dining Table", "dining_table", "1602872030490-4a484a7b3ba6",
             "Pale ash dining table with slim tapered legs and four chairs.", ["ash", "scandinavian", "white"],
             "140 x 80 x 74 cm", 74900, 59900, **pool(11, 5, [(8, 7500), (16, 15000)])),
    _product(NORDLUND, "Ebonised Dining Table", "dining_table", "1615066390971-03e4e1c36ddf",
             "Black-stained ash table with matching chairs.", ["ash", "black", "modern"],
             "170 x 90 x 75 cm", 97900, 78900, **hidden(8, 3)),

    # --- Tables ---
    _product(OAK, "Rustic Oak Coffee Table", "table", "1777513538143-8525eb3943f6",
             "Chunky solid oak coffee table with a low shelf.", ["oak", "rustic"],
             "110 x 60 x 42 cm", 42900, 33900, **pool(13, 7, [(6, 4000), (14, 8500)])),
    _product(OAK, "Low Walnut Coffee Table", "table", "1758565811033-84d1365000c6",
             "Low-profile walnut coffee table with rounded corners.", ["walnut", "mid-century"],
             "100 x 55 x 38 cm", 47900, 37900, **pool(17, 3, [(6, 4500), (15, 9500)])),
    _product(NORDLUND, "Ash Coffee Table", "table", "1581428982868-e410dd047a90",
             "Light ash coffee table that sits beside a sofa.", ["ash", "scandinavian"],
             "90 x 50 x 40 cm", 38900, 30900, **hidden(10, 1)),
    _product(RELOFT, "Steel-Frame Coffee Table", "table", "1594125674956-61a9b49c8ecc",
             "Wooden top on a yellow powder-coated steel frame.", ["industrial", "steel", "yellow"],
             "105 x 55 x 40 cm", 32900, 25900, **pool(6, 4, [(5, 3000), (12, 6500)])),
    _product(OAK, "Walnut Side Table", "table", "1611486212557-88be5ff6f941",
             "Compact walnut side table, finished with hard-wax oil.", ["walnut", "minimal"],
             "45 x 45 x 52 cm", 24900, 19900, **pool(13, 7, [(6, 2500), (15, 5000)])),
    _product(OAK, "Solid Oak Side Table", "table", "1611486212355-d276af4581c0",
             "Small oak side table with a single drawer.", ["oak", "traditional"],
             "40 x 40 x 55 cm", 19900, 15900, **pool(15, 2, [(6, 2000), (14, 4000)])),

    # --- Desks ---
    _product(NORDLUND, "Birch Writing Desk", "desk", "1784012980517-005c26585344",
             "Compact birch desk with a cable drawer.", ["birch", "minimal"],
             "120 x 60 x 74 cm", 69900, 49900, **hidden(8, 3)),
    _product(RELOFT, "Restored Teak Desk", "desk", "1766431015004-315aa01141f9",
             "Danish-style teak desk, sanded and re-oiled.", ["teak", "mid-century", "refurbished"],
             "135 x 65 x 74 cm", 64900, 50900, **pool(9, 2, [(4, 7000), (10, 14000)])),
    _product(OAK, "Oak Writing Bureau", "desk", "1772475385509-93fd87a2d4ba",
             "Solid oak desk with built-in shelving.", ["oak", "traditional"],
             "140 x 65 x 76 cm", 79900, 63900, **pool(3, 5, [(5, 8000), (12, 16000)], late_fill=8, settle=True)),
    _product(NORDLUND, "Oak Standing Desk", "desk", "1772475385529-92037713a057",
             "Height-adjustable desk with a solid oak top.", ["oak", "standing", "office"],
             "160 x 75 x 72-120 cm", 84900, 67900, **hidden(10, 7)),
    _product(NORDLUND, "Compact Pine Desk", "desk", "1598016677484-ad34c3fd766e",
             "Small pine desk sized for a laptop and a notebook.", ["pine", "compact"],
             "100 x 55 x 74 cm", 34900, 27900, **pool(18, 3, [(6, 3500), (14, 7000)])),

    # --- Bookshelves ---
    _product(OAK, "Solid Oak Bookshelf", "bookshelf", "1588580000645-4562a6d2c839",
             "Five-shelf bookshelf in solid oak.", ["oak", "traditional"],
             "180 x 90 x 30 cm", 89900, 69900, **pool(14, 6, [(8, 10000), (20, 20000)])),
    _product(OAK, "Walnut Bookcase", "bookshelf", "1603058817990-2b9a9abbce86",
             "Tall walnut bookcase with adjustable shelves.", ["walnut", "mid-century"],
             "200 x 90 x 32 cm", 104900, 83900, **pool(22, 4, [(6, 10500), (14, 21000)])),
    _product(NORDLUND, "White Ash Bookcase", "bookshelf", "1602722053020-af31042989d5",
             "White-stained ash bookcase with an open back.", ["ash", "white", "scandinavian"],
             "180 x 80 x 30 cm", 59900, 47900, **pool(4, 5, [(8, 6000), (18, 12000)])),
    _product(RELOFT, "Refurbished Bookcase", "bookshelf", "1545696648-86c761bc5410",
             "White painted bookcase, repaired and repainted.", ["painted", "white", "refurbished"],
             "170 x 75 x 28 cm", 34900, 26900, **pool(11, 3, [(5, 4000), (10, 8000)])),
    _product(NORDLUND, "Birch Open Shelving", "bookshelf", "1593430980369-68efc5a5eb34",
             "Open birch shelving unit for books and plants.", ["birch", "open", "minimal"],
             "160 x 70 x 30 cm", 42900, 34900, **hidden(10, 2)),

    # --- Storage ---
    _product(OAK, "Oak Sideboard", "storage", "1767963758785-b9def36c13e3",
             "Oak sideboard with three drawers and two cupboards.", ["oak", "traditional"],
             "160 x 45 x 80 cm", 109900, 87900, **pool(15, 9, [(8, 11000), (16, 22000)])),
    _product(OAK, "Walnut Media Console", "storage", "1758974782657-e5ada4b01c3c",
             "Walnut media console with open shelves and a cable cut-out.", ["walnut", "mid-century"],
             "170 x 40 x 55 cm", 94900, 75900, **pool(20, 4, [(6, 9500), (14, 19000)])),
    _product(RELOFT, "Retro Sideboard", "storage", "1628152371231-936cf45eb8f3",
             "1970s wooden sideboard with sliding doors.", ["retro", "wood", "refurbished"],
             "150 x 45 x 78 cm", 69900, 55900, **hidden(10, 5)),
    _product(RELOFT, "Mid-Century Cabinet", "storage", "1713810958247-01dbd76b4a61",
             "Tall wooden cabinet with two doors, restored.", ["mid-century", "wood", "refurbished"],
             "100 x 40 x 120 cm", 59900, 47900, **pool(12, 4, [(5, 6000), (12, 12000)])),
    _product(NORDLUND, "Oak TV Stand", "storage", "1698674545316-0c93e4ef25a3",
             "Low oak TV stand that fits a 55-inch screen.", ["oak", "scandinavian"],
             "140 x 40 x 48 cm", 47900, 37900, **pool(10, 5, [(6, 5000), (14, 10000)])),

    # --- Bedroom ---
    _product(OAK, "Maple Bed Frame", "bedroom", "1631048499455-4f9e26f23b9f",
             "Queen maple bed frame with a slatted base.", ["maple", "scandinavian"],
             "215 x 165 x 90 cm", 99900, 79900, **pool(20, 6, [(8, 10000), (18, 20000)])),
    _product(NORDLUND, "Black Steel Bed Frame", "bedroom", "1530629013299-6cb10d168419",
             "Queen bed frame in black powder-coated steel.", ["steel", "black", "industrial"],
             "210 x 160 x 95 cm", 54900, 43900, **pool(14, 3, [(6, 5500), (14, 11000)])),
    _product(NORDLUND, "Linen Upholstered Bed", "bedroom", "1560185128-e173042f79dd",
             "Queen bed with a tall linen-upholstered headboard.", ["linen", "beige", "upholstered"],
             "220 x 170 x 115 cm", 119900, 95900, **pool(17, 5, [(8, 12000), (18, 24000)])),
    _product(OAK, "Oak Wardrobe", "bedroom", "1558997519-83ea9252edf8",
             "Two-door oak wardrobe with a hanging rail and a shelf.", ["oak", "traditional"],
             "100 x 55 x 190 cm", 79900, 63900, **hidden(10, 0)),
    _product(OAK, "Cedar Chest of Drawers", "bedroom", "1544691560-fc2053d97726",
             "Five-drawer chest in aromatic cedar.", ["cedar", "traditional"],
             "90 x 45 x 120 cm", 64900, 51900, **hidden(10, 6)),
    _product(OAK, "Oak Nightstand", "bedroom", "1593194632872-3d19dab6e278",
             "Two-drawer oak nightstand.", ["oak", "minimal"],
             "45 x 38 x 55 cm", 22900, 17900, **pool(9, 7, [(6, 2500), (14, 5000)])),

    # --- Lighting ---
    _product(NORDLUND, "Matte Black Floor Lamp", "lighting", "1494438639946-1ebd1d20bf85",
             "Slim black floor lamp with a linen shade.", ["black", "minimal"],
             "30 x 30 x 160 cm", 18900, 14900, **pool(18, 5, [(6, 2000), (14, 4000)])),
    _product(RELOFT, "Brushed Steel Floor Lamp", "lighting", "1630578877871-1a2f9d372fd2",
             "Brushed steel floor lamp with a white shade, rewired.", ["steel", "white", "refurbished"],
             "32 x 32 x 165 cm", 16900, 13900, **pool(12, 2, [(5, 1500), (12, 3000)])),
    _product(NORDLUND, "Felt Dome Pendant", "lighting", "1513506003901-1e6a229e2d15",
             "Soft white dome pendant light.", ["white", "minimal", "scandinavian"],
             "45 x 45 x 30 cm", 12900, 10300, **hidden(10, 0)),
    _product(OAK, "Brass Pendant Trio", "lighting", "1540932239986-30128078f3c5",
             "Three brass pendant lamps on one canopy.", ["brass", "warm"],
             "60 x 20 x 100 cm", 21900, 16900, **pool(16, 3, [(5, 2500), (12, 5000)])),
]
