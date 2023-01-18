package main

import (
	"io"
	"net/http"

	"github.com/Danny-Dasilva/CycleTLS/cycletls"
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
	client := cycletls.Init()

	body, err := io.ReadAll(request.Body)
	if err != nil {
		panic(err)
	}

	response, err := client.Do("https://api.snailtrail.art/graphql/", cycletls.Options{
		Body:      string(body),
		Ja3:       "771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-51-57-47-53-10,0-23-65281-10-11-35-16-5-51-43-13-45-28-21,29-23-24-25-256-257,0",
		UserAgent: "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:87.0) Gecko/20100101 Firefox/87.0",
		Headers: map[string]string{
			"Accept":       "application/json",
			"Content-Type": "application/json",
		},
		Timeout: 5,
	}, "POST")
	if err != nil {
		panic(err)
	}

	if err != nil {
		panic(err)
	}
	w.WriteHeader(response.Status)
	for name, h := range response.Headers {
		w.Header().Add(name, h)
	}

	w.Write([]byte(response.Body))
}

func main() {
	http.HandleFunc("/", hello)
	http.ListenAndServe(":8090", nil)
}
