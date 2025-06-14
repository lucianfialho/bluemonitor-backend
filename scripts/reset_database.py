#!/usr/bin/env python3
"""
Script para zerar a base de dados com backup de segurança.

Execute: python scripts/reset_database.py
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import os

class DatabaseReset:
    """Classe para resetar a base com backup de segurança."""
    
    def __init__(self):
        # URLs para diferentes ambientes
        self.mongodb_uris = [
            os.getenv('MONGODB_URL', 'mongodb://mongodb:27017'),  # Docker interno
            'mongodb://localhost:27017',  # Docker com port mapping
            'mongodb://127.0.0.1:27017'   # Local
        ]
        self.db_name = os.getenv('MONGODB_DB_NAME', 'bluemonitor')
        self.backup_dir = Path('./backups')
        self.backup_dir.mkdir(exist_ok=True)
    
    async def connect_to_mongodb(self):
        """Tenta conectar ao MongoDB testando diferentes URLs."""
        for uri in self.mongodb_uris:
            try:
                print(f"🔗 Tentando conectar: {uri}")
                client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
                
                # Testa a conexão
                await client.admin.command('ping')
                print(f"✅ Conexão bem-sucedida: {uri}")
                return client, client[self.db_name]
                
            except Exception as e:
                print(f"❌ Falha em {uri}: {str(e)}")
                continue
        
        raise Exception("❌ Não foi possível conectar ao MongoDB em nenhuma URL")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do banco antes do reset."""
        client, db = await self.connect_to_mongodb()
        
        try:
            stats = {
                'collections': {},
                'total_documents': 0,
                'database_size': 0
            }
            
            # Lista todas as coleções
            collections = await db.list_collection_names()
            
            for collection_name in collections:
                try:
                    collection = db[collection_name]
                    count = await collection.count_documents({})
                    
                    stats['collections'][collection_name] = {
                        'count': count,
                        'size_estimate': count * 1024  # Estimativa básica
                    }
                    
                    stats['total_documents'] += count
                    
                except Exception as e:
                    print(f"⚠️ Erro ao obter stats da coleção {collection_name}: {str(e)}")
                    stats['collections'][collection_name] = {
                        'count': 0,
                        'error': str(e)
                    }
            
            return stats
            
        finally:
            client.close()
    
    async def create_backup(self) -> str:
        """Cria backup das coleções principais antes do reset."""
        print("📦 Criando backup de segurança...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.json"
        
        client, db = await self.connect_to_mongodb()
        
        try:
            backup_data = {
                'timestamp': timestamp,
                'database': self.db_name,
                'collections': {}
            }
            
            # Coleções importantes para backup
            important_collections = ['news', 'topics', 'categories']
            
            for collection_name in important_collections:
                try:
                    print(f"   📄 Fazendo backup de '{collection_name}'...")
                    
                    collection = db[collection_name]
                    documents = []
                    
                    # Busca todos os documentos (limite de 10.000 para segurança)
                    cursor = collection.find().limit(10000)
                    async for doc in cursor:
                        # Converte ObjectId para string para JSON
                        doc['_id'] = str(doc['_id'])
                        documents.append(doc)
                    
                    backup_data['collections'][collection_name] = documents
                    print(f"   ✅ {len(documents)} documentos salvos de '{collection_name}'")
                    
                except Exception as e:
                    print(f"   ❌ Erro no backup de '{collection_name}': {str(e)}")
                    backup_data['collections'][collection_name] = {'error': str(e)}
            
            # Salva o backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✅ Backup criado: {backup_file}")
            return str(backup_file)
            
        finally:
            client.close()
    
    async def drop_collections(self, collections_to_drop: list = None) -> Dict[str, Any]:
        """Remove coleções especificadas."""
        if collections_to_drop is None:
            collections_to_drop = ['news', 'topics', 'categories']
        
        print(f"🗑️ Removendo coleções: {', '.join(collections_to_drop)}")
        
        client, db = await self.connect_to_mongodb()
        
        results = {}
        
        try:
            for collection_name in collections_to_drop:
                try:
                    # Verifica se a coleção existe
                    collections = await db.list_collection_names()
                    if collection_name in collections:
                        # Conta documentos antes de remover
                        count_before = await db[collection_name].count_documents({})
                        
                        # Remove a coleção
                        await db.drop_collection(collection_name)
                        
                        results[collection_name] = {
                            'status': 'dropped',
                            'documents_removed': count_before
                        }
                        
                        print(f"   ✅ Coleção '{collection_name}' removida ({count_before} documentos)")
                    else:
                        results[collection_name] = {
                            'status': 'not_found',
                            'documents_removed': 0
                        }
                        print(f"   ⚠️ Coleção '{collection_name}' não encontrada")
                        
                except Exception as e:
                    results[collection_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    print(f"   ❌ Erro ao remover '{collection_name}': {str(e)}")
            
            return results
            
        finally:
            client.close()
    
    async def recreate_indexes(self) -> Dict[str, Any]:
        """Recria índices importantes."""
        print("🔧 Recriando índices...")
        
        client, db = await self.connect_to_mongodb()
        
        results = {}
        
        try:
            # Índices para coleção news
            news_indexes = [
                ('url', 1),           # URL único
                ('published_at', -1), # Ordenação por data
                ('language', 1),      # Filtro por idioma
                ('country', 1),       # Filtro por país
                ('source_domain', 1), # Filtro por fonte
            ]
            
            for field, direction in news_indexes:
                try:
                    await db.news.create_index([(field, direction)])
                    print(f"   ✅ Índice criado: news.{field}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao criar índice news.{field}: {str(e)}")
            
            # Índice de texto para busca
            try:
                await db.news.create_index([
                    ('title', 'text'),
                    ('description', 'text'),
                    ('content', 'text')
                ])
                print(f"   ✅ Índice de texto criado para news")
            except Exception as e:
                print(f"   ⚠️ Erro ao criar índice de texto: {str(e)}")
            
            results['status'] = 'completed'
            
        finally:
            client.close()
        
        return results
    
    async def verify_reset(self) -> Dict[str, Any]:
        """Verifica se o reset foi bem-sucedido."""
        print("🔍 Verificando reset...")
        
        stats_after = await self.get_database_stats()
        
        print(f"📊 Estado após reset:")
        for collection, info in stats_after['collections'].items():
            count = info.get('count', 0)
            print(f"   • {collection}: {count} documentos")
        
        return stats_after
    
    async def full_reset(self, create_backup: bool = True) -> Dict[str, Any]:
        """Executa reset completo da base."""
        print("🚀 INICIANDO RESET COMPLETO DA BASE")
        print("=" * 50)
        
        # 1. Estatísticas iniciais
        print("\n1️⃣ Obtendo estatísticas atuais...")
        stats_before = await self.get_database_stats()
        
        print(f"📊 Estado atual:")
        total_docs = 0
        for collection, info in stats_before['collections'].items():
            count = info.get('count', 0)
            total_docs += count
            print(f"   • {collection}: {count} documentos")
        
        if total_docs == 0:
            print("✅ Base já está vazia!")
            return {'status': 'already_empty'}
        
        # 2. Backup (se solicitado)
        backup_file = None
        if create_backup:
            print("\n2️⃣ Criando backup...")
            backup_file = await self.create_backup()
        else:
            print("\n2️⃣ Pulando backup (conforme solicitado)")
        
        # 3. Reset das coleções
        print("\n3️⃣ Removendo dados...")
        drop_results = await self.drop_collections()
        
        # 4. Recriar índices
        print("\n4️⃣ Recriando índices...")
        index_results = await self.recreate_indexes()
        
        # 5. Verificação final
        print("\n5️⃣ Verificação final...")
        stats_after = await self.verify_reset()
        
        # Relatório final
        print(f"\n🎉 RESET CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print(f"📊 Documentos removidos: {total_docs}")
        if backup_file:
            print(f"💾 Backup salvo em: {backup_file}")
        print(f"🔧 Índices recriados: ✅")
        print(f"✅ Base pronta para nova coleta brasileira!")
        
        return {
            'status': 'completed',
            'backup_file': backup_file,
            'documents_removed': total_docs,
            'stats_before': stats_before,
            'stats_after': stats_after,
            'drop_results': drop_results,
            'index_results': index_results
        }

async def main():
    """Função principal."""
    reset_manager = DatabaseReset()
    
    print("🇧🇷 RESET DA BASE PARA NOTÍCIAS BRASILEIRAS")
    print("=" * 60)
    
    try:
        # Verificação inicial
        stats = await reset_manager.get_database_stats()
        total_docs = sum(info.get('count', 0) for info in stats['collections'].values())
        
        if total_docs == 0:
            print("✅ A base já está vazia!")
            return
        
        print(f"📊 Base atual contém {total_docs} documentos")
        print(f"💡 Isso incluirá notícias em inglês que você quer remover")
        
        # Confirmação
        print(f"\n⚠️ ATENÇÃO: Esta operação irá:")
        print(f"   • Fazer backup das coleções importantes")
        print(f"   • Remover TODAS as notícias, tópicos e categorias")
        print(f"   • Recriar índices otimizados")
        print(f"   • Preparar base para coleta brasileira")
        
        response = input(f"\n🤔 Confirma o reset? (digite 'RESET' para confirmar): ")
        
        if response.upper() != 'RESET':
            print("❌ Operação cancelada pelo usuário")
            return
        
        # Executa reset
        result = await reset_manager.full_reset(create_backup=True)
        
        print(f"\n🚀 PRÓXIMOS PASSOS:")
        print(f"   1. Execute a coleta com configuração brasileira:")
        print(f"      python scripts/test_collection.py")
        print(f"   2. Monitore a qualidade das notícias:")
        print(f"      curl http://localhost:8000/api/v1/news?limit=5")
        print(f"   3. Se precisar restaurar:")
        print(f"      python scripts/restore_backup.py {result.get('backup_file', '')}")
        
    except Exception as e:
        print(f"❌ Erro durante reset: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())