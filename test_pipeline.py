#!/usr/bin/env python3
"""
Script de prueba para ejecutar pipelines MongoDB directamente.
Permite probar pipelines antes de usarlos en el MCP server.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
import json

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.config.settings import settings


async def test_pipeline(pipeline):
    """
    Ejecuta un pipeline en MongoDB y muestra los resultados.
    
    Args:
        pipeline: Lista de etapas del pipeline de MongoDB
    """
    client = None
    try:
        # Conectar a MongoDB
        print("🔌 Conectando a MongoDB...")
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]
        collection = db[settings.mongodb_view]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Conectado a MongoDB")
        print(f"   Base de datos: {settings.mongodb_database}")
        print(f"   Colección/Vista: {settings.mongodb_view}")
        print()
        
        # Mostrar pipeline
        print("📋 Pipeline a ejecutar:")
        print(json.dumps(pipeline, indent=2, default=str))
        print()
        
        # Verificar tipos de fechas
        print("🔍 Verificando tipos de datos en el pipeline:")
        def check_types(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if isinstance(value, datetime):
                        print(f"   ✅ {current_path}: datetime ({value})")
                    elif isinstance(value, str) and ('date' in key.lower() or 'time' in key.lower()):
                        print(f"   ⚠️  {current_path}: string ({value}) - DEBERÍA SER datetime")
                    elif isinstance(value, (dict, list)):
                        check_types(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_types(item, f"{path}[{i}]")
        
        check_types(pipeline)
        print()
        
        # Ejecutar pipeline
        print("🚀 Ejecutando pipeline...")
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        
        print(f"✅ Pipeline ejecutado exitosamente")
        print(f"   Documentos retornados: {len(results)}")
        print()
        
        if results:
            print("📄 Primer documento:")
            print(json.dumps(results[0], indent=2, default=str))
            print()
            if len(results) > 1:
                print(f"   ... y {len(results) - 1} documentos más")
        else:
            print("⚠️  No se retornaron documentos")
            print()
            print("💡 Posibles causas:")
            print("   - Las fechas no coinciden con los datos")
            print("   - Los filtros son muy restrictivos")
            print("   - El formato de fechas no es correcto")
        
        return results
        
    except PyMongoError as e:
        print(f"❌ Error de MongoDB: {e}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if client:
            client.close()
            print("\n🔌 Desconectado de MongoDB")


async def test_with_isodate():
    """Prueba con ISODate (formato que funciona en MongoDB Compass)"""
    print("=" * 70)
    print("TEST 1: Pipeline con ISODate (formato que funciona en Compass)")
    print("=" * 70)
    print()
    
    # Crear fechas como datetime objects (equivalente a ISODate en Python)
    start_date = datetime(2025, 11, 24, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2025, 11, 27, 23, 59, 59, tzinfo=timezone.utc)
    
    pipeline = [
        {
            "$match": {
                "createdAt": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        },
        {
            "$sort": {"createdAt": 1}
        },
        {
            "$limit": 10
        }
    ]
    
    await test_pipeline(pipeline)


async def test_with_string_dates():
    """Prueba con strings (formato que NO debería funcionar)"""
    print("\n" + "=" * 70)
    print("TEST 2: Pipeline con strings (formato que NO funciona)")
    print("=" * 70)
    print()
    
    pipeline = [
        {
            "$match": {
                "createdAt": {
                    "$gte": "2025-11-24 00:00:00+00:00",
                    "$lte": "2025-11-27 23:59:59+00:00"
                }
            }
        },
        {
            "$sort": {"createdAt": 1}
        },
        {
            "$limit": 10
        }
    ]
    
    await test_pipeline(pipeline)


async def test_simple_query():
    """Prueba simple sin filtros de fecha"""
    print("\n" + "=" * 70)
    print("TEST 3: Query simple sin filtros de fecha")
    print("=" * 70)
    print()
    
    pipeline = [
        {
            "$limit": 5
        }
    ]
    
    await test_pipeline(pipeline)


if __name__ == "__main__":
    print("🧪 Script de prueba de pipelines MongoDB")
    print("=" * 70)
    print()
    
    # Cargar variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    # Ejecutar tests
    asyncio.run(test_simple_query())
    asyncio.run(test_with_isodate())
    asyncio.run(test_with_string_dates())

