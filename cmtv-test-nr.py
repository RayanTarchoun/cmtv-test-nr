import json
import logging
import os
import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

session = requests.Session()
folder = os.path.dirname(os.path.abspath(__file__)) + '/'

def load_config():
    with open(folder + 'config.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_token(config):
    try:
        logging.info("Tentative de récupération du token...")
        response = session.post(
            url=config['token_url'],
            data={
                'grant_type': 'client_credentials',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'scope': config['scope']
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10,
            verify=False
        )
        response.raise_for_status()
        token = response.json().get('access_token')
        logging.info("Token récupéré avec succès.")
        return token
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la récupération du token : {e}")
        raise

def call_api(server, token, data):
    try:
        response = session.post(
            url=f"{server}/api/analyses",
            json=data,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=10,
            verify=False
        )
        return {
            "status_code": response.status_code,
            "response": response.json() if response.content else None
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur API : {e.response.status_code if e.response else 'N/A'} - {e.response.text if e.response else str(e)}")
        return {
            "status_code": e.response.status_code if e.response else 'N/A',
            "error": e.response.text if e.response else str(e)
        }

def compare_json(json1, json2):
    differences = {k: {'ref': json1.get(k), 'version': json2.get(k)} for k in json1.keys() | json2.keys() if json1.get(k) != json2.get(k)}
    return differences if differences else None

def process(config, usecase, usecases):
    try:
        data = usecases.get(usecase)
        if not data:
            raise ValueError(f'{usecase} non trouvé')

        # Vérifier si le résultat existe déjà dans le fichier JSON
        if "result" in data and "http_code" in data:
            logging.info(f"Résultat existant trouvé pour le {usecase}")
            result_data = {
                "status_code": data["http_code"],
                "response": data["result"]
            }
        else:
            # Si le résultat n'existe pas, exécuter la requête pour le récupérer
            logging.info(f"Aucun résultat trouvé pour le {usecase}, récupération en cours...")
            result_data = call_api(config['url_ref'], config['token'], data)
            if "response" in result_data:
                # Sauvegarder le résultat dans le fichier JSON
                data["result"] = result_data["response"]
                data["http_code"] = result_data["status_code"]
                with open(folder + 'usecases.json', 'w', encoding='utf-8') as f:
                    json.dump(usecases, f, indent=2, ensure_ascii=False)
                logging.info(f"Résultat sauvegardé pour le UseCase {usecase}")

        # Appel API pour la version
        version_result = call_api(config['url_version'], config['token'], data)

        # Gestion des erreurs HTTP
        if result_data["status_code"] != 200 or version_result["status_code"] != 200:
            logging.warning(f"Erreur HTTP pour le {usecase}")
            logging.warning(f"Référence - Code HTTP : {result_data['status_code']}, Réponse : {result_data.get('response') or result_data.get('error')}")
            logging.warning(f"Version - Code HTTP : {version_result['status_code']}, Réponse : {version_result.get('response') or version_result.get('error')}")
            return 1

        # Sauvegarder le résultat de la version dans le champ 'result', même en cas d'erreur
        data["result"] = version_result.get("response", {"error": version_result.get("error", "Erreur inconnue")})
        with open(folder + 'usecases.json', 'w', encoding='utf-8') as f:
            json.dump(usecases, f, indent=2, ensure_ascii=False)
        logging.info(f"Résultat mis à jour pour le {usecase}")

        # Comparaison des réponses JSON
        differences = compare_json(result_data.get("response", {}), version_result.get("response", {}))
        if differences:
            logging.info(f"Différences détectées pour le {usecase} : {differences}")
            print(f"\n=== Résultats pour le : {usecase} ===")
            print(f"Référence:\n{json.dumps(result_data.get('response', {}), indent=2, ensure_ascii=False)}")
            print(f"Version:\n{json.dumps(version_result.get('response', {}), indent=2, ensure_ascii=False)}")
            print(f"\n--- Différences détectées ---\n{json.dumps(differences, indent=2, ensure_ascii=False)}")
            return 1
        else:
            print(f"\n=== {usecase} : Aucune différence détectée ===")
            return 0
    except Exception as e:
        logging.error(f"Erreur sur le UseCase {usecase} : {e}")
        data = usecases.get(usecase, {})
        data["result"] = {"error": str(e)}  # Enregistrer l'erreur dans le champ 'result'
        with open(folder + 'usecases.json', 'w', encoding='utf-8') as f:
            json.dump(usecases, f, indent=2, ensure_ascii=False)
        print(f"\nErreur sur le {usecase} : {e}")
        print(f"Données du UseCase : {json.dumps(data, indent=2, ensure_ascii=False)}")
        return 1

if __name__ == "__main__":
    try:
        with open(folder + 'usecases.json', 'r', encoding='utf-8') as f:
            usecases = json.load(f)

        config = load_config()

        print("Récupération du token...")
        config['token'] = get_token(config)
        print("Token récupéré avec succès.")

        total_errors = 0  # Compteur pour les erreurs et différences

        for usecase in usecases:
            print(f"\n=== Début du traitement pour {usecase} ===")
            try:
                result = process(config, usecase, usecases)
                total_errors += result  # Comptabiliser les erreurs ou différences détectées
            except Exception as e:
                logging.error(f"Erreur inattendue lors du traitement du UseCase {usecase} : {e}")
                print(f"Erreur inattendue pour le UseCase {usecase} : {e}")
                total_errors += 1
            print(f"=== Fin du traitement pour {usecase} ===")

        if total_errors > 0:
            print(f"\n=== Résumé : {total_errors} différences ou erreurs détectées ===")
        else:
            print("\n=== Résumé : Aucune différence ou erreur détectée ===")

        exit(0)  # Code de sortie pour succès
    except Exception as e:
        logging.error(f"Erreur générale : {e}")
        print(f"Erreur générale : {e}")
        exit(1)  # Code de sortie pour une erreur globale