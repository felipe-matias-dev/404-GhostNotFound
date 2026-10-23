from typing import Annotated

from pydantic import StringConstraints

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
