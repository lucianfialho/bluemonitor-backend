"""Categories endpoints."""
from fastapi import APIRouter, HTTPException, status

# Cópia estática das categorias para melhor desempenho
CATEGORIES = {
    'Saúde': {
        'keywords': ['saúde', 'médico', 'tratamento', 'terapia', 'autismo', 'TEA', 'diagnóstico', 'intervenção', 'saudável'],
        'description': 'Notícias sobre saúde, tratamentos e bem-estar relacionados ao autismo'
    },
    'Direitos': {
        'keywords': ['direito', 'lei', 'legislação', 'jurídico', 'justiça', 'direitos humanos', 'inclusão', 'acessibilidade'],
        'description': 'Direitos legais e questões jurídicas relacionadas ao autismo'
    },
    'Tecnologia': {
        'keywords': ['tecnologia', 'app', 'aplicativo', 'software', 'hardware', 'inovação', 'digital', 'tecnológico'],
        'description': 'Tecnologias e inovações que auxiliam pessoas com autismo'
    },
    'Educação': {
        'keywords': ['educação', 'escola', 'ensino', 'aprendizado', 'professor', 'aluno', 'pedagogia', 'inclusão escolar'],
        'description': 'Educação inclusiva e estratégias de ensino para autistas'
    },
    'Pesquisa': {
        'keywords': ['pesquisa', 'estudo', 'científico', 'ciência', 'descoberta', 'universidade', 'pesquisador'],
        'description': 'Pesquisas e descobertas científicas sobre autismo'
    },
    'Família': {
        'keywords': ['família', 'pais', 'mãe', 'pai', 'filho', 'cuidadores', 'casa', 'lar'],
        'description': 'Orientações e experiências para famílias de pessoas com autismo'
    },
    'Inclusão': {
        'keywords': ['inclusão', 'acessibilidade', 'inclusivo', 'diversidade', 'equidade', 'oportunidades'],
        'description': 'Iniciativas e práticas de inclusão social para autistas'
    }
}

IRRELEVANT_KEYWORDS = [
    'futebol', 'esporte', 'celebridade', 'entretenimento', 'novela', 'cinema',
    'música', 'show', 'festival', 'bbb', 'big brother', 'lazer', 'viagem', 'turismo'
]

router = APIRouter(tags=["categories"])

@router.get("", response_model=dict)
async def list_categories():
    """List all available categories for topic classification.
    
    Returns:
        A dictionary with the list of categories and their keywords.
        
    Example response:
    {
        "categories": {
            "Saúde": {
                "keywords": ["saúde", "médico", ...],
                "description": "Notícias sobre saúde..."
            },
            ...
        },
        "irrelevant_keywords": ["futebol", "esporte", ...]
    }
    """
    try:
        return {
            "categories": CATEGORIES,
            "irrelevant_keywords": IRRELEVANT_KEYWORDS
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve categories: {str(e)}"
        )
