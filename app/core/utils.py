import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Regex para datas relativas em português (ex: '2 dias atrás', '3 horas atrás')
RELATIVE_DATE_REGEX = re.compile(r"(\d+)\s+(segundos|minutos|horas|dias|semanas|meses|anos)\s+atrás", re.IGNORECASE)

# Mapear unidades para timedelta
RELATIVE_UNITS = {
    'segundos': 'seconds',
    'minutos': 'minutes',
    'horas': 'hours',
    'dias': 'days',
    'semanas': 'weeks',
    'meses': 'days',  # Aproximação: 30 dias
    'anos': 'days',   # Aproximação: 365 dias
}
RELATIVE_MULTIPLIER = {
    'meses': 30,
    'anos': 365
}

def parse_date_string(date_input: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Converte uma string de data (ou datetime) para datetime UTC.
    Suporta ISO, formato brasileiro, e datas relativas em português.
    Retorna None se não conseguir converter.
    """
    if date_input is None:
        return None
    if isinstance(date_input, datetime):
        return date_input
    if not isinstance(date_input, str):
        logger.warning(f"Tipo de data não suportado: {type(date_input)}")
        return None
    date_str = date_input.strip()
    # 1. ISO 8601
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    # 2. Formato brasileiro: dd/mm/yyyy [hh:mm[:ss]]
    try:
        if re.match(r"\d{2}/\d{2}/\d{4}", date_str):
            for fmt in ["%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
    except Exception:
        pass
    # 3. Relativo em português: '2 dias atrás', '3 horas atrás'
    m = RELATIVE_DATE_REGEX.match(date_str)
    if m:
        value = int(m.group(1))
        unit = m.group(2).lower()
        if unit in RELATIVE_UNITS:
            kw = {RELATIVE_UNITS[unit]: value * RELATIVE_MULTIPLIER.get(unit, 1)}
            dt = datetime.utcnow() - timedelta(**kw)
            return dt.replace(tzinfo=timezone.utc)
    # 4. Fallback: tentar parsing genérico
    try:
        import dateutil.parser
        dt = dateutil.parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    logger.warning(f"Falha ao converter data: {date_str}")
    return None
