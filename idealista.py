import requests, traceback, os, csv, argparse
from bs4 import BeautifulSoup
from time import sleep
from datetime import date
from collections import OrderedDict
from progress.bar import FillingSquaresBar
from progress.counter import Pie 

class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\x1B[3m'

TEMPLATE_VIVIENDA = {
	'titulo':'-',
	'habitaciones':'-',
	'metros':'-',
	'planta':'-',
	'agencia':'-',
	'calle_agencia':'-',
	'cod_postal_agencia':'-',
	'telefono':'-',
	'precio':'-',
	'descripcion':'-',
	'enlace':'-',
	'enlace_agencia':'-'
}

TEMPLATE_AGENCIA = {
	'nombre':'-',
	'telefono':'-',
	'direccion':'-',
	'cod_postal':'-',
	'municipio':'-',
	'num_anuncios':'0',
	'enlace':'-'
}

AGENCIAS = {}

def lanzar_peticion(url,session,i):
	headers = {
		'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0'
	}


	try:
		page = session.get(url,headers=headers)
	except Exception as e:
		raise Exception('Error no esperado al hacer la petición: {}'.format(e))

	status = str(page.status_code)
	if status == '403':
		raise StopIteration('Petición bloqueada!')
	elif status == '404':
		raise StopIteration('Página no encontrada!')
	elif page.history:
		if i == 1:
			pass
		else:
			raise StopIteration('FIN')

	soup = BeautifulSoup(page.text, 'html.parser')

	return soup

def lanzar_peticion_generica(url):
	s = requests.Session()
	soup = ''
	try:
		sleep(2)
		soup = lanzar_peticion(url,s,0)
	except StopIteration as e:
		if 'FIN' in str(e):
			return soup,'particular'
		else:
			raise Exception(e)
	return soup,'agencia'

def loading_bar():
    cont = Pie("\rObteniendo listado de viviendas ")
    for num in range(100):
        cont.next()
        sleep(.02)

def lanzar_peticiones_listado(url):
	s = requests.Session()

	result = []
	i = 1
	error = 0

	while True:
		url2 = url.replace('XXX',str(i))
		
		try:
			loading_bar()
			soup = lanzar_peticion(url2,s,i)
		except StopIteration as e:
			if i == 1:
				raise Exception(e)
			if str(e) == 'FIN':
				break
			else:
				print ('{}Se ha obtenido {} páginas de resultados, pero con errores{}'.format(bcolors.YELLOW,i-1,bcolors.END))
				error = 1
				break

		result.append(soup)
		i = i + 1

	if not error:
		print ('\n{}Se han obtenido {} páginas de resultados{}'.format(bcolors.GREEN,i-1,bcolors.END))
	return result

def obtener_viviendas(soup):
	articles = soup.find_all('article')

	viviendas = []

	for article in articles:
		if 'item' in article.get('class'):
			vivienda = TEMPLATE_VIVIENDA.copy()

			links = article.find_all('a')
			for link in links: 
				title = link.get('title')
				if title:
					vivienda['titulo'] = title
					vivienda['enlace'] = 'https://www.idealista.com{}'.format(link.get('href'))
				if 'tel' in link.get('href'):
					vivienda['telefono'] = link.get('href').split(':')[1]
				if 'pro' in link.get('href'):
					vivienda['agencia'] = link.get('title')
					vivienda['enlace_agencia'] = 'https://www.idealista.com{}'.format(link.get('href'))

			spans = article.find_all('span')
			for span in spans:
				c = span.get('class')
				if c:
					if 'item-price' in c:
						vivienda['precio'] = span.text
					elif 'item-detail' in c:
						if 'hab' in span.text:
							vivienda['habitaciones'] = span.text.split(' ')[0]
						elif 'planta' in span.text or 'bajo' in span.text.lower() or 'exterior' in span.text:
							vivienda['planta'] = span.text.split(' ')[0]
						elif 'm' in span.text:
							vivienda['metros'] = span.text
			
			ps = article.find_all('p')
			for p in ps:
				c = p.get('class')
				if c and 'ellipsis' in c:
					vivienda['descripcion'] = p.text

			viviendas.append(vivienda)

	return viviendas

def obtener_agencia(soup,tipo):
	global AGENCIAS
	agencia = TEMPLATE_AGENCIA.copy()

	if tipo == 'particular':
		agencia['nombre'] = 'particular'

	else:
		title = soup.find('h3')
		agencia['nombre'] = title.text

		p = soup.find_all('p')
		if len(p) == 5:
			agencia['telefono'] = p[0].text.split(':')[1]
			agencia['cod_postal'] = p[2].text
			agencia['municipio'] = p[3].text
			agencia['enlace'] = p[4].find('a').get('href')
			agencia['direccion'] = p[1].text
			agencia['num_anuncios'] = '1'

			for key in agencia.keys():
				if not agencia[key]:
					agencia[key] = '-'
		
			# Añadir al diccionario global
			AGENCIAS[agencia['telefono']] = agencia
	
	return agencia

def generar_url(url):
	return '{}{}'.format(url,'pagina-XXX.htm?ordenado-por=fecha-publicacion-desc')

def ordenar_diccionario(data):
	r = []
	for d in data:
		ordenado = OrderedDict(sorted(d.items()))
		r.append(ordenado)
	return r

def json_to_csv(data,name_csv):
	name = '{}_{}.csv'.format(name_csv,date.today().strftime("%d_%m_%Y"))
	current_path = os.getcwd()
	path = os.path.join(current_path,name)
	if data:
		try:
			with open(path,'w') as f:
				output = csv.writer(f)
				output.writerow(data[0].keys())
				for row in data:
					output.writerow(row.values())
		except Exception as e:
			raise Exception('Error al exportar a CSV: {}'.format(e))

		print ('{}Se ha exportado correctamente en {}{}'.format(bcolors.GREEN,path,bcolors.END))
	else:
		raise Exception('No se ha podido exportar a CSV debido a que no se han obtenido resultados')


def obtener_detalles_agencias(r):
	agencias = []
	url = 'https://www.idealista.com/telefono-inmueble/XXX/?freeTextSearchType=PHONE'
	agencia = {}	
	if not '-' in r['telefono']:
		# Check cache
		if r['telefono'] in AGENCIAS.keys():
			AGENCIAS[r['telefono']]['num_anuncios'] = str(int(AGENCIAS[r['telefono']]['num_anuncios']) + 1)
			agencia = AGENCIAS[r['telefono']]
		else:
			url2 = url.replace('XXX',r['telefono'])
			soup,tipo = lanzar_peticion_generica(url2)
			agencia = obtener_agencia(soup,tipo)
			if tipo == 'particular':
				agencia['telefono'] = r['telefono']
			agencias.append(agencia)

	# Actualizar listado 
	if agencia:
		r['agencia'] = agencia['nombre']
		r['calle_agencia'] = agencia['direccion']
		r['cod_postal_agencia'] = agencia['cod_postal']
		r['enlace_agencia'] = agencia['enlace']

	return agencias

if __name__ == '__main__':
	print('{}Bienvenido al extractor de viviendas y locales de Idealista!{}'.format(bcolors.BOLD,bcolors.END))
	print('{}Versión 1.0{}\n'.format(bcolors.ITALIC,bcolors.END))

	parser = argparse.ArgumentParser()
	parser.add_argument('--url', help='URL de www.idealista.com', required=True)
	parser.add_argument('-n','--nombre', help='Nombre fichero de salida', default='', type=str)
	parser.add_argument('-a', '--agencias', help='Buscar información sobre las agencias', default=False, action='store_true')
	args = parser.parse_args()

	if not args.nombre:
		name = args.url.split('/')[-2]
	else:
		name = args.nombre

	nombre_csv_listado = '{}_listado'.format(name)
	nombre_csv_agencias = '{}_agencias'.format(name)


	try:
		
		# Obtener listado
		resultado = []
		url = generar_url(args.url)
		soup = lanzar_peticiones_listado(url)
		
		m = len(soup)
		bar = FillingSquaresBar('Obteniendo información de viviendas', max=m)
		for s in soup:
			sleep(.5)
			listado = obtener_viviendas(s)
			resultado = resultado + listado
			bar.next()
		bar.finish()
		
		# Exportar a CSV listado ver1
		json_to_csv(resultado,nombre_csv_listado)

		# Obtener detalles agencia
		if args.agencias:
			m = len(resultado)
			bar = FillingSquaresBar('Obteniendo información de agencias', max=m)
			for r in resultado:
				agencias = obtener_detalles_agencias(r)
				bar.next()
			bar.finish()
			
			# Exportar a CSV listado ver2
			json_to_csv(resultado,nombre_csv_listado)

			# Exportar a CSV agencias
			agencias = []
			for key in AGENCIAS.keys():
				agencias.append(AGENCIAS[key])
			json_to_csv(agencias,nombre_csv_agencias)

		

	except Exception as e:
		print ('{}✘ {}{}'.format(bcolors.RED,e,bcolors.END))
		#traceback.print_exc()
	

		
		




