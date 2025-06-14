#!/usr/bin/env python3
import coverage
import pytest

if __name__ == "__main__":
    # Inicia a cobertura
    cov = coverage.Coverage()
    cov.start()
    
    # Executa os testes
    pytest.main(["tests/unit/services/news/test_collector.py", "-v"])
    
    # Para a cobertura e gera o relatório
    cov.stop()
    cov.save()
    
    # Gera relatório detalhado
    print("\n" + "="*80)
    print("Relatório de Cobertura")
    print("="*80)
    cov.report()
    
    # Gera relatório HTML
    cov.html_report(directory='coverage_html')
    print("\nRelatório HTML gerado em: coverage_html/index.html")
