export function parseOpenApiEndpoints(spec) {
  const endpoints = {};
  const HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];

  for (const [path, operations] of Object.entries(spec.paths)) {
    for (const [httpMethod, operation] of Object.entries(operations)) {
      if (!HTTP_METHODS.includes(httpMethod)) continue;

      const name = operation.summary
        .toLowerCase()
        .split(' ')
        .map((w, i) => i === 0 ? w : w.charAt(0).toUpperCase() + w.slice(1))
        .join('');

      // Separar params por ubicación: path, query
      const params = { path: [], query: [] };
      for (const param of operation.parameters ?? []) {
        params[param.in]?.push(param.name);
      }

      // Body: sacar el nombre del schema referenciado
      const bodyRef = operation.requestBody?.content?.['application/json']?.schema?.['$ref'];
      const body = bodyRef ? bodyRef.split('/').pop() : null;

      endpoints[name] = {
        method: httpMethod.toUpperCase(),
        path,
        ...(params.path.length  && { pathParams:  params.path  }),
        ...(params.query.length && { queryParams: params.query }),
        ...(body                && { body }),
      };
    }
  }

  return endpoints;
}


const BASE_URL = 'http://localhost:8000';
export async function callEndpoint({ //destructuring, method = obj.method, path = obj.path, queryParams = obj.queryParams o null por default
  method, 
  path, 
  pathParams = null, 
  queryParams = null,
  headers = null, 
  body = null}) {

    // Reemplazar path params: /crosbal/{id}/crosbaleano/{path} → /crosbal/1/crosbaleano/foo
    const resolvedPath = path.replace(/\{(\w+)\}/g, function(match, key) {
      if (pathParams && pathParams[key] != null) {
          return pathParams[key];
      }
      return `{${key}}`;
    });

    // Armar URL con query params
    const url = new URL(BASE_URL + resolvedPath);
    if (queryParams) {
      for (const [key, value] of Object.entries(queryParams)) {
        if (value !== null && value !== undefined) url.searchParams.set(key, value);
      }
    }

    // Fetch
    try{
      const response = await fetch(url, {
        method,
        headers: {
          ...(headers || {}),
          ...(body ? { 'Content-Type': 'application/json' } : {})
        },
        body: body ? JSON.stringify(body) : null,
      });
      
    // const response = await fetch(url);
    // fetch(url) devuelve:
    // Promise<Response>
    // Pero el await hace esto:
    // await Promise<Response>  →  Response
    // Entonces:
    // response es un objeto Response normal
    // No es Promise
    // No es thenable

      if (!response.ok) throw { status: response.status};
      const data = await response.json();
      //promise.
      return data

      // async function ejemplo() {
      //   return data;
      // }
      // Es equivalente a:
      // function ejemplo() {
      //   return Promise.resolve(data);
      // }
    }
    catch(err){

      if (err.name === 'TypeError'){
        throw {
          status: "Error de red o CORS"
        }
      }
      console.log(err);
      throw err;
    }
}

// // Usar con fetch:
// const { method, path } = endpoints.obtenerAccesorio;
// const url = `http://localhost:8000${path.replace('{accesorio_id}', 5)}`;
// const accesorio = await fetch(url, { method }).then(r => r.json());
//Nunca hagas fetch automático al importar un módulo helper.


export async function loadSpec() {
  try {
    console.log("CROBAL 1");
    const response = await fetch('http://localhost:8000/openapi.json');    
    if (!response.ok) {
      throw new Error("Error en la respuesta");
    }
    const spec = await response.json();

    return parseOpenApiEndpoints(spec);
  }
    
  catch (err){
    console.log(`HUBO ERROR ${err}`)
    throw err;
  }
  // DEVUELVE UN OBJETO ERROR EN CASO DE ERROR
}

let cachedSpecs = null;
// en el peor caso varios componentes pueden lanzar el fetch de loadSpec si varios acceden al mismo tiempo
// cuando cachedSpecs es null
// quizas se puede arreglar cacheando la promise
export async function getSpecsNormal() {
  if (!cachedSpecs) {
    const parsed = await loadSpec(); // vale err si hubo error
    cachedSpecs = parsed;
  }
  return cachedSpecs;
}

// cacheando promise: (NO HACE FALTA SI USO CONTEXT)
let specsPromise = null;

export function getSpecs() {
  if (!specsPromise) {
    specsPromise = loadSpec();
  }
  return specsPromise;
}

// //Ejemplo
// actualizarAccesorio: Object { method: "PATCH", path: "/accesorios/{accesorio_id}", body: "AccesorioUpdate", … }
// actualizarSubtipoAccesorio: Object { method: "PATCH", path: "/subtipos-accesorios/{subtipo_id}", body: "SubtipoAccesorioUpdate", … }
// actualizarTipoAccesorio: Object { method: "PATCH", path: "/tipos-accesorios/{tipo_id}", pathParams: (1) […], … }
// crearAccesorio: Object { method: "POST", path: "/accesorios/", body: "AccesorioCreate" }
// crearSubtipoAccesorio: Object { method: "POST", path: "/subtipos-accesorios/", body: "SubtipoAccesorioCreate" }
// crearTipoAccesorio: Object { method: "POST", path: "/tipos-accesorios/", body: "TipoAccesorioCreate" }
// eliminarAccesorio: Object { method: "DELETE", path: "/accesorios/{accesorio_id}", pathParams: (1) […] }
// eliminarSubtipoAccesorio: Object { method: "DELETE", path: "/subtipos-accesorios/{subtipo_id}", pathParams: (1) […] }
// eliminarTipoAccesorio: Object { method: "DELETE", path: "/tipos-accesorios/{tipo_id}", pathParams: (1) […] }
// listarAccesorios: Object { method: "GET", path: "/accesorios/", queryParams: (3) […] }
// listarSubtiposAccesorios: Object { method: "GET", path: "/subtipos-accesorios/", queryParams: (4) […] }
// listarTiposAccesorios: Object { method: "GET", path: "/tipos-accesorios/", queryParams: (3) […] }
// obtenerAccesorio: Object { method: "GET", path: "/accesorios/{accesorio_id}", pathParams: (1) […] }
// obtenerSubtipoAccesorio: Object { method: "GET", path: "/subtipos-accesorios/{subtipo_id}", pathParams: (1) […] }
// obtenerTipoAccesorio: Object { method: "GET", path: "/tipos-accesorios/{tipo_id}", pathParams: (1) […] }
// sugerirNombreAccesorio: Object { method: "POST", path: "/accesorios/sugerir-nombre", body: "AccesorioCreate" }
// verificarDuplicado: Object { method: "POST", path: "/accesorios/verificar-duplicado", body: "AccesorioCreate" }