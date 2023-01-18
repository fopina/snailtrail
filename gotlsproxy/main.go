package main

import (
	"io"
	"net/http"
	"time"
)

func hello(w http.ResponseWriter, req *http.Request) {
	request, err := http.NewRequest("POST", "https://api.snailtrail.art/graphql/", req.Body)
	if err != nil {
		panic(err)
	}
	for name, headers := range req.Header {
		for _, h := range headers {
			request.Header.Add(name, h)
		}
	}
	client := http.Client{
		Timeout: time.Duration(5 * time.Second),
	}
	response, err := client.Do(request)
	if err != nil {
		panic(err)
	}
	data, err := io.ReadAll(response.Body)
	if err != nil {
		panic(err)
	}
	w.WriteHeader(response.StatusCode)
	for name, headers := range response.Header {
		for _, h := range headers {
			w.Header().Add(name, h)
		}
	}

	w.Write(data)
}

func main() {
	http.HandleFunc("/", hello)
	http.ListenAndServe(":8090", nil)
}
