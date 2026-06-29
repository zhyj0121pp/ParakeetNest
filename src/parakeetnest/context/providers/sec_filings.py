"""SEC filing context provider backed by the SEC Filing Layer service."""

from __future__ import annotations

from parakeetnest.context.models import (
    ContextMetadata,
    ContextRequest,
    FilingItem,
    FilingSnapshot,
    MeetingContext,
)
from parakeetnest.context.provider import (
    ContextProviderResult,
    UnsupportedContextRequestError,
)
from parakeetnest.sec.models import SecFiling
from parakeetnest.sec.service import SecFilingService


class SecFilingContextProvider:
    """Build filing context from provider-backed SecFilingService metadata."""

    provider_name = "sec_filings"

    def __init__(
        self,
        sec_filing_service: SecFilingService,
        *,
        recent_8k_limit: int = 3,
    ) -> None:
        self._sec_filing_service = sec_filing_service
        self._recent_8k_limit = recent_8k_limit

    def supports(self, request: ContextRequest) -> bool:
        return bool(request.symbols)

    def build_context(self, request: ContextRequest) -> ContextProviderResult:
        if not self.supports(request):
            raise UnsupportedContextRequestError(self.provider_name, request)

        filings = tuple(self._filings_for_request(request))
        fetched_at = request.as_of or max(
            (filing.filed_at for filing in filings),
            default=None,
        )
        partial_context = MeetingContext(
            request=request,
            metadata=ContextMetadata(
                generated_at=fetched_at,
                sources=(self.provider_name,),
            ),
            filings=FilingSnapshot(
                source=self.provider_name,
                fetched_at=fetched_at,
                items=tuple(self._item_for(filing) for filing in filings),
            ),
        )
        return ContextProviderResult(
            provider_name=self.provider_name,
            partial_context=partial_context,
            metadata={"source": "sec_filing_service"},
        )

    def _filings_for_request(self, request: ContextRequest) -> list[SecFiling]:
        filings: list[SecFiling] = []
        for symbol in request.symbols:
            latest_10k = self._sec_filing_service.get_latest_10k(symbol)
            if latest_10k is not None:
                filings.append(latest_10k)

            latest_10q = self._sec_filing_service.get_latest_10q(symbol)
            if latest_10q is not None:
                filings.append(latest_10q)

            filings.extend(
                self._sec_filing_service.get_recent_8k(
                    symbol,
                    limit=self._recent_8k_limit,
                )
            )
        return filings

    def _item_for(self, filing: SecFiling) -> FilingItem:
        return FilingItem(
            symbol=filing.symbol,
            filing_type=filing.filing_type.value,
            source=filing.provider or self.provider_name,
            filed_at=filing.filed_at,
            accession_number=filing.accession_number,
            url=filing.filing_url or filing.document_url,
            summary=filing.title,
        )
