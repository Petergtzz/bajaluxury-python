from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

# A JSON number for clients; Decimal inside, so sums stay exact to the cent.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
