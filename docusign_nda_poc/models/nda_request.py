"""
NDA Request/Response Models
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EnvelopeStatus(str, Enum):
    """DocuSign envelope status"""

    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"


@dataclass
class Signer:
    """Signer information"""

    name: str
    email: str
    recipient_id: Optional[str] = None

    def __post_init__(self):
        if not self.recipient_id:
            self.recipient_id = str(hash(self.email) % 10000)


@dataclass
class SignaturePosition:
    """Signature tab position using anchor string or fixed coordinates"""

    # TODO: 本番環境では、VC/PharmaがアップロードするNDA PDFに埋め込むアンカータグを
    #       事前に決定し、ガイドラインとして提供する必要がある。
    #       例: 「署名欄の位置に /sn1/ と白文字で記載してください」
    #       現在はサンプルPDF (World_Wide_Corp_lorem.pdf) に合わせて /sn1/ を使用。

    # アンカー方式（anchor_string が None でない場合に使用）
    anchor_string: Optional[str] = "/sn1/"
    anchor_units: str = "pixels"
    anchor_x_offset: str = "20"
    anchor_y_offset: str = "10"

    # 固定座標方式（anchor_string が None の場合に使用）
    # None の場合は Free Form Signing（署名者が位置を決める）
    page_number: Optional[str] = None
    x_position: Optional[str] = None
    y_position: Optional[str] = None

    @property
    def use_anchor(self) -> bool:
        """アンカー方式を使用するかどうか"""
        return self.anchor_string is not None

    @property
    def use_fixed_position(self) -> bool:
        """固定座標方式を使用するかどうか"""
        return (
            self.anchor_string is None
            and self.page_number is not None
            and self.x_position is not None
            and self.y_position is not None
        )

    @property
    def use_free_form(self) -> bool:
        """Free Form Signing（署名者が位置を決める）を使用するかどうか"""
        return self.anchor_string is None and not self.use_fixed_position

    @classmethod
    def free_form(cls) -> "SignaturePosition":
        """Free Form Signing用のインスタンスを作成（全フィールド表示）"""
        return cls(anchor_string=None)

    @classmethod
    def fixed(cls, page: int = 1, x: int = 100, y: int = 700) -> "SignaturePosition":
        """固定座標用のインスタンスを作成"""
        return cls(
            anchor_string=None,
            page_number=str(page),
            x_position=str(x),
            y_position=str(y),
        )


@dataclass
class DateSignedPosition:
    """Date signed tab position using anchor string or fixed coordinates"""

    # TODO: 日付欄用のアンカータグも本番では別途定義が必要。
    #       例: /dn1/ を日付記入欄の位置に埋め込んでもらう。
    #       現在はサンプルPDFに日付用アンカーがないため、署名欄と同じタグで
    #       オフセットをずらして配置している（暫定対応）。

    # アンカー方式
    anchor_string: Optional[str] = "/sn1/"
    anchor_units: str = "pixels"
    anchor_x_offset: str = "120"
    anchor_y_offset: str = "10"

    # 固定座標方式
    page_number: Optional[str] = None
    x_position: Optional[str] = None
    y_position: Optional[str] = None

    @property
    def use_anchor(self) -> bool:
        return self.anchor_string is not None

    @property
    def use_fixed_position(self) -> bool:
        return (
            self.anchor_string is None
            and self.page_number is not None
            and self.x_position is not None
            and self.y_position is not None
        )

    @property
    def use_free_form(self) -> bool:
        return self.anchor_string is None and not self.use_fixed_position

    @classmethod
    def free_form(cls) -> "DateSignedPosition":
        """Free Form用（日付欄なし）"""
        return cls(anchor_string=None)

    @classmethod
    def fixed(cls, page: int = 1, x: int = 200, y: int = 700) -> "DateSignedPosition":
        """固定座標用のインスタンスを作成"""
        return cls(
            anchor_string=None,
            page_number=str(page),
            x_position=str(x),
            y_position=str(y),
        )


@dataclass
class WebhookConfig:
    """Webhook (EventNotification) configuration for envelope-level Connect"""

    # Webhook URL to receive notifications
    url: str

    # Events to trigger webhook
    envelope_events: list[str] = field(
        default_factory=lambda: ["completed", "declined", "voided"]
    )

    # Include signed documents in webhook payload (large payload)
    include_documents: bool = False

    # Enable logging in DocuSign
    logging_enabled: bool = True

    # Require acknowledgment (retry if no 200 response)
    require_acknowledgment: bool = True


@dataclass
class NDARequest:
    """
    NDA envelope creation request.

    Supports Recipient Group for multiple signers where
    only one signature is required.
    """

    # Document
    document_base64: str
    document_name: str = "NDA_秘密保持契約書.pdf"

    # Email settings
    email_subject: str = "【DCP】NDA締結のお願い"
    email_blurb: str = "秘密保持契約書への署名をお願いいたします。"

    # Signers (Recipient Group members)
    signers: list[Signer] = field(default_factory=list)

    # Recipient Group name
    group_name: str = "Academia/Startup Signers"

    # Signature position
    signature_position: SignaturePosition = field(default_factory=SignaturePosition)
    date_signed_position: DateSignedPosition = field(default_factory=DateSignedPosition)

    # Initial status (sent = immediately send, created = draft)
    status: EnvelopeStatus = EnvelopeStatus.SENT

    # Webhook configuration (optional, but recommended for production)
    webhook_config: Optional[WebhookConfig] = None

    def add_signer(self, name: str, email: str) -> "NDARequest":
        """Add a signer to the recipient group"""
        self.signers.append(Signer(name=name, email=email))
        return self

    def set_webhook(self, url: str, **kwargs) -> "NDARequest":
        """Set webhook URL for envelope-level notifications"""
        self.webhook_config = WebhookConfig(url=url, **kwargs)
        return self


@dataclass
class EnvelopeResponse:
    """Response from envelope creation"""

    envelope_id: str
    status: EnvelopeStatus
    status_datetime: Optional[datetime] = None
    uri: Optional[str] = None

    @classmethod
    def from_api_response(cls, response) -> "EnvelopeResponse":
        """Create from DocuSign API response"""
        status_dt = None
        if response.status_date_time:
            try:
                status_dt = datetime.fromisoformat(
                    response.status_date_time.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return cls(
            envelope_id=response.envelope_id,
            status=EnvelopeStatus(response.status),
            status_datetime=status_dt,
            uri=getattr(response, "uri", None),
        )
